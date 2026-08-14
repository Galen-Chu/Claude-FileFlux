# Enhanced Rename - Replace Mode Implementation Plan

## Overview

Add a "Replace" mode to the rename functionality that allows users to find and replace text in filenames, complementing the existing prefix/suffix modes.

---

## Feature Specification

### User Interface

**Rename Modal Updates:**
- Mode selection: Radio buttons for Prefix / Suffix / **Replace**
- When "Replace" is selected, show:
  - **Find text** input: Text to search for in filename
  - **Replace with** input: Text to replace it with
  - **Case sensitive** checkbox: Toggle case-sensitive matching (default: false)
  - **Use regex** checkbox: Enable regular expressions (default: false, advanced)
  - **Replace all occurrences** checkbox: Replace all matches or just first (default: true)

### Behavior Examples

**Simple Replace (Case-insensitive):**
```
Filename: MyDocument_V1.pdf
Find: "v1"
Replace with: "v2"
Result: MyDocument_V2.pdf
```

**Replace with Empty String (Delete text):**
```
Filename: file_backup_2024.txt
Find: "_backup"
Replace with: ""
Result: file_2024.txt
```

**Replace Multiple Occurrences:**
```
Filename: test_test_test.txt
Find: "test"
Replace with: "doc"
Replace all: true
Result: doc_doc_doc.txt
```

**Replace with Sequence:**
```
Filenames: report_draft.pdf, summary_draft.pdf
Find: "draft"
Replace with: "final"
+ Add sequence: true
Result: report_final_001.pdf, summary_final_002.pdf
```

**Case-Sensitive Replace:**
```
Filename: TestFile.txt
Find: "test" (case-sensitive: true)
Replace with: "demo"
Result: TestFile.txt (no change - "test" not found, only "Test")
```

**Regex Replace (Advanced):**
```
Filename: IMG_2024_0303_photo.jpg
Find regex: "IMG_(\d{4})_(\d{4})"
Replace with: "PHOTO_\1_\2"
Result: PHOTO_2024_0303_photo.jpg
```

---

## Implementation Details

### 1. Service Layer Changes

**Update `BaseStorage.rename_files()` signature:**
```python
def rename_files(
    self,
    files: List[str],
    text: str,
    mode: str = 'prefix',  # Now: 'prefix', 'suffix', or 'replace'
    add_sequence: bool = False,
    start_number: int = 1,
    # New parameters for replace mode
    find_text: str = None,
    case_sensitive: bool = False,
    use_regex: bool = False,
    replace_all: bool = True
) -> dict:
    pass
```

**Implementation in `local_storage.py` and `s3_storage.py`:**

```python
def rename_files(self, files, text, mode='prefix', add_sequence=False,
                 start_number=1, find_text=None, case_sensitive=False,
                 use_regex=False, replace_all=True):
    result = {'success': [], 'failed': []}

    for index, file_path in enumerate(files):
        try:
            # Get filename
            original_name = file_path.split('/')[-1]

            # Split name and extension
            if '.' in original_name:
                name_parts = original_name.rsplit('.', 1)
                name_without_ext = name_parts[0]
                extension = '.' + name_parts[1]
            else:
                name_without_ext = original_name
                extension = ''

            # Apply transformation based on mode
            if mode == 'prefix':
                new_name = text + name_without_ext
            elif mode == 'suffix':
                new_name = name_without_ext + text
            elif mode == 'replace':
                if not find_text:
                    raise ValueError("find_text is required for replace mode")

                # Perform replacement
                if use_regex:
                    import re
                    flags = 0 if case_sensitive else re.IGNORECASE
                    count = 0 if replace_all else 1
                    new_name = re.sub(find_text, text, name_without_ext,
                                     count=count, flags=flags)
                else:
                    if case_sensitive:
                        if replace_all:
                            new_name = name_without_ext.replace(find_text, text)
                        else:
                            new_name = name_without_ext.replace(find_text, text, 1)
                    else:
                        # Case-insensitive replacement
                        import re
                        pattern = re.escape(find_text)
                        count = 0 if replace_all else 1
                        new_name = re.sub(pattern, text, name_without_ext,
                                         count=count, flags=re.IGNORECASE)

            # Add sequence if requested
            if add_sequence:
                sequence_num = start_number + index
                new_name = new_name + f'_{sequence_num:03d}'

            # Add extension back
            new_name = new_name + extension

            # Rest of rename logic...
```

### 2. Serializer Changes

**Update `BulkRenameRequestSerializer`:**
```python
class BulkRenameRequestSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.CharField())
    text = serializers.CharField(max_length=100)
    mode = serializers.ChoiceField(
        choices=['prefix', 'suffix', 'replace'],
        default='prefix'
    )
    add_sequence = serializers.BooleanField(default=False)
    start_number = serializers.IntegerField(default=1, min_value=0)
    source = serializers.CharField()

    # Replace mode specific fields
    find_text = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Text to find (required for replace mode)'
    )
    case_sensitive = serializers.BooleanField(
        default=False,
        help_text='Case-sensitive matching (replace mode only)'
    )
    use_regex = serializers.BooleanField(
        default=False,
        help_text='Treat find_text as regular expression'
    )
    replace_all = serializers.BooleanField(
        default=True,
        help_text='Replace all occurrences or just the first'
    )

    def validate(self, data):
        if data['mode'] == 'replace' and not data.get('find_text'):
            raise serializers.ValidationError(
                "find_text is required when mode is 'replace'"
            )
        return data
```

### 3. API Changes

**Update `FileManagementViewSet.rename()`:**
```python
@action(detail=False, methods=['post'])
def rename(self, request):
    serializer = BulkRenameRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data

    result = storage.rename_files(
        files=data['files'],
        text=data['text'],
        source=data['source'],
        mode=data['mode'],
        add_sequence=data['add_sequence'],
        start_number=data['start_number'],
        find_text=data.get('find_text'),
        case_sensitive=data.get('case_sensitive', False),
        use_regex=data.get('use_regex', False),
        replace_all=data.get('replace_all', True)
    )

    return Response(result)
```

### 4. Frontend Changes

**Update Rename Modal HTML:**
```html
<!-- Mode Selection -->
<div class="mb-4">
    <label class="block text-sm font-medium text-gray-700 mb-2">Mode</label>
    <div class="space-y-2">
        <label class="flex items-center">
            <input type="radio" name="rename-mode" value="prefix" checked>
            <span class="ml-2">Prefix (add before name)</span>
        </label>
        <label class="flex items-center">
            <input type="radio" name="rename-mode" value="suffix">
            <span class="ml-2">Suffix (add after name)</span>
        </label>
        <label class="flex items-center">
            <input type="radio" name="rename-mode" value="replace">
            <span class="ml-2">Replace (find and replace text)</span>
        </label>
    </div>
</div>

<!-- Text Input (Prefix/Suffix mode) -->
<div id="text-input-group" class="mb-4">
    <label class="block text-sm font-medium text-gray-700 mb-2">Text to Add</label>
    <input type="text" id="rename-text" placeholder="e.g., new_ or _backup">
</div>

<!-- Replace Mode Inputs (Hidden by default) -->
<div id="replace-inputs" class="hidden">
    <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">Find Text</label>
        <input type="text" id="find-text" placeholder="Text to search for">
        <p class="mt-1 text-xs text-gray-500">Text to find in filenames</p>
    </div>

    <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">Replace With</label>
        <input type="text" id="replace-text" placeholder="Replacement text">
        <p class="mt-1 text-xs text-gray-500">Leave empty to delete the found text</p>
    </div>

    <div class="mb-4 space-y-2">
        <label class="flex items-center">
            <input type="checkbox" id="case-sensitive" class="w-4 h-4">
            <span class="ml-2 text-sm text-gray-700">Case sensitive</span>
        </label>

        <label class="flex items-center">
            <input type="checkbox" id="replace-all" checked class="w-4 h-4">
            <span class="ml-2 text-sm text-gray-700">Replace all occurrences</span>
        </label>

        <label class="flex items-center">
            <input type="checkbox" id="use-regex" class="w-4 h-4">
            <span class="ml-2 text-sm text-gray-700">Use regular expression</span>
        </label>
    </div>
</div>

<!-- Sequence Options (Same as before) -->
<!-- ... -->
```

**JavaScript Functions:**
```javascript
// Handle mode change
document.querySelectorAll('input[name="rename-mode"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const replaceInputs = document.getElementById('replace-inputs');
        const textGroup = document.getElementById('text-input-group');

        if (this.value === 'replace') {
            replaceInputs.classList.remove('hidden');
            textGroup.classList.add('hidden');
        } else {
            replaceInputs.classList.add('hidden');
            textGroup.classList.remove('hidden');
        }
    });
});

// Confirm rename with replace parameters
async function confirmRename(event) {
    event.preventDefault();

    const mode = document.querySelector('input[name="rename-mode"]:checked').value;
    const addSequence = document.getElementById('add-sequence').checked;
    const startNumber = parseInt(document.getElementById('start-number').value) || 1;

    let requestData = {
        files: files,
        mode: mode,
        add_sequence: addSequence,
        start_number: startNumber,
        source: source
    };

    if (mode === 'replace') {
        requestData.text = document.getElementById('replace-text').value;
        requestData.find_text = document.getElementById('find-text').value;
        requestData.case_sensitive = document.getElementById('case-sensitive').checked;
        requestData.replace_all = document.getElementById('replace-all').checked;
        requestData.use_regex = document.getElementById('use-regex').checked;
    } else {
        requestData.text = document.getElementById('rename-text').value;
    }

    // Send request...
}
```

---

## Testing Plan

### Unit Tests

```python
# manager/tests/test_rename_replace.py

def test_simple_replace():
    """Test basic find and replace"""
    result = storage.rename_files(
        files=['document_v1.txt'],
        text='v2',
        mode='replace',
        find_text='v1',
        source='local'
    )
    assert result['success'][0]['new_path'] == 'document_v2.txt'

def test_case_insensitive_replace():
    """Test case-insensitive replacement"""
    result = storage.rename_files(
        files=['TestFile.TXT'],
        text='new',
        mode='replace',
        find_text='test',
        case_sensitive=False,
        source='local'
    )
    assert result['success'][0]['new_path'] == 'newFile.TXT'

def test_replace_with_sequence():
    """Test replace combined with sequence numbering"""
    result = storage.rename_files(
        files=['file_draft.txt', 'doc_draft.txt'],
        text='final',
        mode='replace',
        find_text='draft',
        add_sequence=True,
        start_number=1,
        source='local'
    )
    assert result['success'][0]['new_path'] == 'file_final_001.txt'
    assert result['success'][1]['new_path'] == 'doc_final_002.txt'

def test_regex_replace():
    """Test regex pattern replacement"""
    result = storage.rename_files(
        files=['IMG_2024_0303_photo.jpg'],
        text='PHOTO_\\1_\\2',
        mode='replace',
        find_text='IMG_(\\d{4})_(\\d{4})',
        use_regex=True,
        source='local'
    )
    assert result['success'][0]['new_path'] == 'PHOTO_2024_0303_photo.jpg'

def test_replace_delete_text():
    """Test replacing with empty string to delete text"""
    result = storage.rename_files(
        files=['file_backup.txt'],
        text='',
        mode='replace',
        find_text='_backup',
        source='local'
    )
    assert result['success'][0]['new_path'] == 'file.txt'
```

### Integration Tests

```bash
# Test simple replace
curl -X POST http://127.0.0.1:8000/api/files/rename/ \
  -H "Content-Type: application/json" \
  -d '{
    "files": ["report_v1.pdf"],
    "mode": "replace",
    "find_text": "v1",
    "text": "v2",
    "source": "local"
  }'

# Test case-insensitive replace
curl -X POST http://127.0.0.1:8000/api/files/rename/ \
  -H "Content-Type: application/json" \
  -d '{
    "files": ["TEST_FILE.txt"],
    "mode": "replace",
    "find_text": "test",
    "text": "demo",
    "case_sensitive": false,
    "source": "local"
  }'

# Test replace with sequence
curl -X POST http://127.0.0.1:8000/api/files/rename/ \
  -H "Content-Type: application/json" \
  -d '{
    "files": ["doc_draft.txt", "file_draft.txt"],
    "mode": "replace",
    "find_text": "draft",
    "text": "final",
    "add_sequence": true,
    "start_number": 1,
    "source": "local"
  }'
```

---

## Security Considerations

1. **Regex Injection**: Validate and sanitize regex patterns
2. **Input Validation**: Limit find_text and replacement text length
3. **Performance**: Set timeout for regex operations
4. **Error Messages**: Don't expose sensitive information in error messages

```python
# In serializer validation
import re

def validate_find_text(self, value):
    # Limit length
    if len(value) > 100:
        raise serializers.ValidationError("Find text too long (max 100 characters)")

    # Validate regex if use_regex is True
    if self.initial_data.get('use_regex'):
        try:
            re.compile(value)
        except re.error as e:
            raise serializers.ValidationError(f"Invalid regex: {str(e)}")

    return value
```

---

## Performance Impact

- **Simple replace**: Minimal overhead (string operations)
- **Regex replace**: May be slower for complex patterns
- **Multiple files**: Linear time complexity O(n)
- **Recommendation**: Limit to 100 files per operation for regex mode

---

## Version Target

**Target Version:** 1.2.0
**Estimated Effort:** 1-2 days
**Breaking Changes:** None (fully backward compatible)

---

## Future Enhancements

- **Preview Mode**: Show preview of renamed files before applying
- **Undo Function**: Allow undoing last rename operation
- **Templates**: Save common replace patterns
- **Batch Patterns**: Apply multiple replace operations in one go
