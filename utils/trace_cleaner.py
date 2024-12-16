def trace_cleaner(trace_path: str):
    import os
    import json
    import zipfile

    # 1. Unzip the trace.zip into a directory named after the zip file (minus extension).
    with zipfile.ZipFile(trace_path, 'r') as zip_ref:
        extracted_dir = os.path.splitext(trace_path)[0]
        zip_ref.extractall(extracted_dir)

    # 2. Delete the zip file.
    os.remove(trace_path)

    # 3. Open "trace.trace" as a JSONL file.
    trace_file_path = os.path.join(extracted_dir, "trace.trace")
    if not os.path.exists(trace_file_path):
        raise FileNotFoundError(f"File not found: {trace_file_path}")

    # Build list of rows we want to keep.
    filtered_rows = []
    with open(trace_file_path, "r", encoding="utf-8") as trace_file:
        for line in trace_file:
            row = json.loads(line)
            if row.get("type") in ["log", "before", "after"]:
                row_str = json.dumps(row)
                # 4. If any of the unwanted strings are present, skip this row entirely.
                if "LocatorAssertions" in row_str or "waiting for" in row_str:
                    continue
            filtered_rows.append(row)

    # Overwrite the file with only the filtered rows.
    with open(trace_file_path, "w", encoding="utf-8") as trace_file:
        for row in filtered_rows:
            trace_file.write(json.dumps(row) + "\n")