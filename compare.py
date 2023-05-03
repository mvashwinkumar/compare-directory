import os
import filecmp
import difflib
import time
import html
import argparse

def get_ruler_span(ruler = '&nbsp;', color = '#8080808a'):
    return f"""
        <div style='color: {color}; display: inline-flex; width: 20px; margin-right: 5px; justify-content: center'>
            &nbsp;{ruler}&nbsp;
        </div>
    """

def compare_dirs(dir1, dir2, output_file):
    style = """
    <style>
        table {
            width: 100%;
            table-layout: fixed;
        }
        .fixTableHead {
            overflow-y: auto;
            height: 110px;
        }
        .fixTableHead thead th {
            position: sticky;
            top: 0;
        }
        .ten {
            width: 10%;
        }
        .twenty {
            width: 20%;
            vertical-align: top;
        }
        /* see me */
        td {
            border: solid;
            word-wrap:break-word
        }

        tr.file-not-found {
            background:rgba(255,153,0,0.4);
        }
        tr.file-no-change {
            background:rgba(0,255,0,0.2);
        }
    </style>
    """

    search_bar = """
    <input type="text" id="searchInput" list="filePaths" onkeyup="filterRows()" placeholder="Search by file path...">
    <datalist id="filePaths"></datalist>
    <script>
        function updateSuggestions(value) {
            let dataList = document.getElementById('filePaths');
            dataList.innerHTML = '';
            let table = document.getElementById('comparisonTable');
            let tr = table.getElementsByTagName('tr');
            
            for (let i = 0; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName('td')[0];
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (txtValue.toUpperCase().includes(value.toUpperCase())) {
                        let option = document.createElement('option');
                        option.value = txtValue;
                        dataList.appendChild(option);
                    }
                }
            }
        }
        function filterRows() {
            let input = document.getElementById('searchInput');
            let filter = input.value.toUpperCase();
            let table = document.getElementById('comparisonTable');
            let tr = table.getElementsByTagName('tr');
        
            for (let i = 0; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName('td')[0];
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (txtValue.toUpperCase().indexOf(filter) > -1) {
                        tr[i].style.display = '';
                    } else {
                        tr[i].style.display = 'none';
                    }
                }
            }

            if (input.value.length >= 3) {
                updateSuggestions(input.value);
            }
        }
    </script>
    """

    table_header = f"""
        <table id='comparisonTable' border='1' class='fixTableHead'>
            <thead>
                <th class='ten'>File Path</th>
                <th class='twenty'>Directory 1 (old): {dir1}</th>
                <th class='twenty'>Directory 2 (new): {dir2}</th>
            </thead>
            <tbody>
        """
    table_rows = []

    for root1, dirs1, files1 in os.walk(dir1):
        root2 = root1.replace(dir1, dir2)
        for file1 in files1:
            file2 = file1
            file_path1 = os.path.join(root1, file1)
            file_path2 = os.path.join(root2, file2)

            if not os.path.exists(file_path2):
                table_rows.append(f"<tr class='file-not-found'><td class='ten'>{file_path1}</td><td class='twenty'><span style='color: red;'>File not found in '{dir2}'</span></td><td class='twenty'></td></tr>")
                continue

            if filecmp.cmp(file_path1, file_path2, shallow=False):
                table_rows.append(f"<tr class='file-no-change'><td class='ten'>{file_path1}</td><td class='twenty'><span>No change</span></td><td class='twenty'><span>No change</span></td></tr>")
            else:
                with open(file_path1, encoding='utf8') as f1, open(file_path2, encoding='utf8') as f2:
                    diff1, diff2 = [], []
                    diff = list(difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file_path1, tofile=file_path2, lineterm='', n=3))
                    for line in diff:
                        if line.startswith('---') or line.startswith('+++'):
                            pass
                        elif line.startswith('@@'):
                            diff1.append(f"<hr><span style='color: grey;'>&nbsp;{html.escape(line)}</span><br>")
                            diff2.append(f"<hr><span style='color: grey;'>&nbsp;{html.escape(line)}</span><br>")
                        elif line.startswith('+'):
                            diff1.append(f'{get_ruler_span()}&nbsp;')
                            diff2.append(f"{get_ruler_span(line[0], '#008000a0')}<span style='color: green;'>{html.escape(line[1:])}</span>")
                        elif line.startswith('-'):
                            diff1.append(f"{get_ruler_span(line[0], '#ff000080')}<span style='color: red;'>{html.escape(line[1:])}</span>")
                            diff2.append(f'{get_ruler_span()}&nbsp;')
                        else:
                            text = f"{get_ruler_span('=')}{html.escape(line[1:])}"
                            diff1.append(text)
                            diff2.append(text)

                    table_rows.append(f"<tr><td class='ten'>{file_path1}</td><td class='twenty'>{'<br>'.join(diff1)}</td><td class='twenty'>{'<br>'.join(diff2)}</td></tr>")

    for root2, dirs2, files2 in os.walk(dir2):
        root1 = root2.replace(dir2, dir1)
        for file2 in files2:
            file1 = file2
            file_path1 = os.path.join(root1, file1)
            file_path2 = os.path.join(root2, file2)

            if not os.path.exists(file_path1):
                table_rows.append(f"<tr class='file-not-found'><td class='ten'>{file_path2}</td><td class='twenty'></td><td class='twenty'><span style='color: red;'>File not found in '{dir1}'</span></td></tr>")

    table_footer = "</tbody></table>"
    html_output = style + search_bar + table_header + "\n".join(table_rows) + table_footer

    with open(output_file, 'w') as f:
        f.write(html_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Compare two directories and generate an HTML report',
        usage='python compare_directories.py path/to/first/directory path/to/second/directory -o my_differences.html'
    )
    parser.add_argument('dir1', help='Path to the first directory.')
    parser.add_argument('dir2', help='Path to the second directory.')
    parser.add_argument('-o', '--output', default='differences.html', help='Path to the output file (default: differences.html).')

    args = parser.parse_args()

    # get the start time
    st = time.time()
    compare_dirs(args.dir1, args.dir2, args.output)
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    print('Execution time:', elapsed_time, 'seconds')
