"""
Bi-directional sync between local storage and S3.

build_plan() diffs the two stores by relative path (last-write-wins by
timestamp); execute() copies accordingly. Timestamps converge after a copy:
a push stamps the local file with the upload time, a pull stamps the local
file with the S3 LastModified carried in the plan, so a follow-up sync sees
the pair as unchanged instead of ping-ponging.
"""
import os

from .exceptions import FileOperationError

# Filesystem and S3 metadata timestamps can jitter by a second or two;
# differences within this window are treated as "unchanged".
EPSILON_SECONDS = 2.0


class SyncService:
    """Plan and execute a bi-directional sync between local storage and S3."""

    def __init__(self, local_storage, s3_storage):
        self.local_storage = local_storage
        self.s3_storage = s3_storage

    @staticmethod
    def _epoch(dt):
        """Normalize a FileInfo.modified_time (naive or tz-aware) to epoch seconds."""
        if dt is None:
            return 0.0
        return dt.timestamp()

    def build_plan(self, path: str = '') -> dict:
        """
        Compare local files and S3 objects by relative path (files only).

        Returns:
            {'actions': [{'path', 'direction': 'push'|'pull',
                          'reason': 'local_only'|'s3_only'|'local_newer'|'s3_newer',
                          's3_ts': float|None}],
             'unchanged': int}
        """
        local_files = {f.path: f for f in self.local_storage.list_files(path) if not f.is_directory}
        s3_files = {f.path: f for f in self.s3_storage.list_files(path) if not f.is_directory}

        actions = []
        unchanged = 0
        for rel_path in sorted(set(local_files) | set(s3_files)):
            local_info = local_files.get(rel_path)
            s3_info = s3_files.get(rel_path)

            if local_info and not s3_info:
                actions.append({'path': rel_path, 'direction': 'push',
                                'reason': 'local_only', 's3_ts': None})
            elif s3_info and not local_info:
                actions.append({'path': rel_path, 'direction': 'pull',
                                'reason': 's3_only', 's3_ts': self._epoch(s3_info.modified_time)})
            else:
                local_ts = self._epoch(local_info.modified_time)
                s3_ts = self._epoch(s3_info.modified_time)
                if abs(local_ts - s3_ts) <= EPSILON_SECONDS:
                    unchanged += 1
                elif local_ts > s3_ts:
                    actions.append({'path': rel_path, 'direction': 'push',
                                    'reason': 'local_newer', 's3_ts': s3_ts})
                else:
                    actions.append({'path': rel_path, 'direction': 'pull',
                                    'reason': 's3_newer', 's3_ts': s3_ts})
        return {'actions': actions, 'unchanged': unchanged}

    def execute(self, plan: dict, dry_run: bool = False) -> dict:
        """
        Execute a plan produced by build_plan().

        Returns:
            {'executed': [{'path', 'direction'}], 'failed': [{'path', 'error'}]}
        """
        executed, failed = [], []

        for action in plan.get('actions', []):
            rel_path = action['path']
            direction = action['direction']

            if dry_run:
                executed.append({'path': rel_path, 'direction': direction, 'dry_run': True})
                continue

            try:
                abs_local = self.local_storage._validate_path(rel_path)  # traversal-safe

                if direction == 'push':
                    self.s3_storage.upload_file(str(abs_local), rel_path)
                    # Converge timestamps: S3 LastModified is the upload time,
                    # so stamp the local file with ~now to match it.
                    now = self._now_epoch()
                    os.utime(abs_local, (now, now))
                elif direction == 'pull':
                    os.makedirs(os.path.dirname(str(abs_local)) or '.', exist_ok=True)
                    self.s3_storage.download_file(rel_path, str(abs_local))
                    # Converge timestamps: stamp the local file with the S3
                    # LastModified carried in the plan so the pair reads unchanged.
                    s3_ts = action.get('s3_ts')
                    if s3_ts:
                        os.utime(abs_local, (s3_ts, s3_ts))
                else:
                    failed.append({'path': rel_path, 'error': f'Unknown direction: {direction}'})
                    continue

                executed.append({'path': rel_path, 'direction': direction})

            except FileOperationError as e:
                failed.append({'path': rel_path, 'error': str(e)})
            except Exception as e:
                failed.append({'path': rel_path, 'error': str(e)})

        return {'executed': executed, 'failed': failed}

    @staticmethod
    def _now_epoch() -> float:
        import time
        return time.time()
