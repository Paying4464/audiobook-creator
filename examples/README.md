# Examples

This directory contains example files to help you get started with the Audiobook Creator.

## Chapter Index File (chapters.tsv)

An example TSV (tab-separated values) file showing how to define custom chapter names and order.

**Format:**
```
filename.mp3<TAB>Chapter Name
```

**Usage:**
```bash
./main.py -i "/path/to/audio/files" -o "output.m4b" -I examples/chapters.tsv
```

## Tips

1. **File Order**: Files in the TSV will be processed in the order they appear
2. **Missing Files**: Files not in the TSV will be added at the end in alphabetical order
3. **Tab Separation**: Make sure to use actual tab characters, not spaces
4. **Chapter Names**: Can include any characters except tabs and newlines
5. **File Extensions**: Must match exactly with the actual audio files

## Creating Your Own Chapter File

1. List your audio files:
   ```bash
   ls -1 /path/to/audio/files/*.mp3 > filelist.txt
   ```

2. Edit the file to add tab-separated chapter names:
   ```
   01-intro.mp3	Introduction
   02-chapter1.mp3	The Beginning
   ```

3. Save as a .tsv file and use with the `-I` option