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

def compare_dirs(dir1, dir2, output_file, ignore_file_extensions=[]):
    stats = {
        'total': 0,
        'ignored': 0,
        'identical': 0,
        'changed': 0,
        'removed': 0,
        'added': 0,
    }

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
            word-wrap:break-word;
        }
        .small {
            width: 1.5rem;
            vertical-align: top;
        }
        .ten {
            vertical-align: top;
        }
        .twenty {
            width: 37.5%;
            vertical-align: top;
        }
        /* see me */
        td {
            border: solid;
            word-wrap:break-word
        }

        .file-ignored {
            background: #8080808a;
        }
        .file-added {
            background:rgba(115,255,0,0.2);
        }
        .file-removed {
            background:rgba(236,2,2,0.2);
        }
        .file-no-change {
            background:rgba(0,0,255,0.2);
        }
        .unselectable {
            opacity: 0;
            -moz-user-select: none;
            -khtml-user-select: none;
            -webkit-user-select: none;

            /*
                Introduced in Internet Explorer 10.
                See http://ie.microsoft.com/testdrive/HTML5/msUserSelect/
            */
            -ms-user-select: none;
            user-select: none;
        }
    </style>
    """

    search_bar = """
    <div style="display: inline-block;">Search:</div>
    <input type="text" id="searchInput" list="filePaths" onkeyup="filterRows()" placeholder="Search by file path...">
    <datalist id="filePaths"></datalist>
    <script>
        function updateSuggestions(value) {
            let dataList = document.getElementById('filePaths');
            dataList.innerHTML = '';
            let table = document.getElementById('comparisonTable');
            let tr = table.getElementsByTagName('tr');
            
            for (let i = 0; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName('td')[1];
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (txtValue.toUpperCase().includes(value.toUpperCase())) {
                        let option = document.createElement('option');
                        option.value = txtValue.trim();
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
                let td = tr[i].getElementsByTagName('td')[1];
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
        <h3>Directory Comparison Report</h3>
        <button id="expandAllBtn" onclick="expandAll()">Expand All</button>
        <button id="collapseAllBtn" onclick="collapseAll()">Collapse All</button>
        <table id='comparisonTable' border='1' class='fixTableHead'>
            <thead>
                <th class='small'></th>
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
                stats['removed'] += 1
                table_rows.append(f"<tr class='file-removed'><td class='small'></td><td class='ten'>{file_path1}</td><td class='twenty' colspan='2' style='text-align: center;'><span>Removed from '{dir2}'</span></td></tr>")
                continue
            
            if os.path.splitext(file_path1)[1][1:] in ignore_file_extensions:
                stats['ignored'] += 1
                table_rows.append(f"<tr class='file-ignored'><td class='small'></td><td class='ten'>{file_path1}</td><td class='twenty' colspan='2' style='text-align: center;'><span>Ignored</span></td></tr>")
            elif filecmp.cmp(file_path1, file_path2, shallow=False):
                stats['identical'] += 1
                table_rows.append(f"<tr class='file-no-change'><td class='small'></td><td class='ten'>{file_path1}</td><td class='twenty' colspan='2' style='text-align: center;'><span>No change</span></td></tr>")
            else:
                stats['changed'] += 1
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
                            diff1.append(f'{get_ruler_span()}<span class="unselectable">{html.escape(line[1:])}</span>')
                            diff2.append(f"{get_ruler_span(line[0], '#008000a0')}<span style='color: green;'>{html.escape(line[1:])}</span>")
                        elif line.startswith('-'):
                            diff1.append(f"{get_ruler_span(line[0], '#ff000080')}<span style='color: red;'>{html.escape(line[1:])}</span>")
                            diff2.append(f'{get_ruler_span()}<span class="unselectable">{html.escape(line[1:])}</span>')
                        else:
                            text = f"{get_ruler_span('=')}{html.escape(line[1:])}"
                            diff1.append(text)
                            diff2.append(text)
                    table_rows.append(f"""
                    <tr>
                        <td class='small'><span class="collapse-icon" onclick="toggleRow(this.parentElement.parentElement, this)" style="cursor:pointer;">[-]</span></td>
                        <td class='ten'>
                            {file_path1}
                        </td>
                        <td class='twenty'>{'<br>'.join(diff1)}</td>
                        <td class='twenty'>{'<br>'.join(diff2)}</td>
                    </tr>
                    """)
                    # table_rows.append(f"<tr><td class='ten'>{file_path1}</td><td class='twenty'>{'<br>'.join(diff1)}</td><td class='twenty'>{'<br>'.join(diff2)}</td></tr>")

    for root2, dirs2, files2 in os.walk(dir2):
        root1 = root2.replace(dir2, dir1)
        for file2 in files2:
            file1 = file2
            file_path1 = os.path.join(root1, file1)
            file_path2 = os.path.join(root2, file2)

            if not os.path.exists(file_path1):
                stats['added'] += 1
                table_rows.append(f"<tr class='file-added'><td class='small'></td><td class='ten'>{file_path2}</td><td class='twenty' colspan='2' style='text-align: center;'><span>Added in '{dir2}'</span></td></tr>")

    table_footer = "</tbody></table>"

    stats['total'] = stats['identical'] + stats['changed'] + stats['added'] + stats['removed'] + stats['ignored']
    stats_div = f"""
        <div id="stats" style="display: flex; justify-content: space-around; align-items: center; margin: 10px 0px; padding: 2px; border: solid 2px black;">
            <div style='padding: 10px; font-weight: bold; text-align: center;'>Total: {stats['total']}</div>
            <div style='padding: 10px; border-radius: 5px; font-weight: bold; text-align: center;'>Changed: {stats['changed']}</div>
            <div class='file-added' style='padding: 10px; border-radius: 5px; font-weight: bold; text-align: center;'>Added: {stats['added']}</div>
            <div class='file-removed' style='padding: 10px; border-radius: 5px; font-weight: bold; text-align: center;'>Removed: {stats['removed']}</div>
            <div class='file-no-change' style='padding: 10px; border-radius: 5px; font-weight: bold; text-align: center;'>Identical: {stats['identical']}</div>
            <div class='file-ignored' style='padding: 10px; border-radius: 5px; font-weight: bold; text-align: center;'>Ignored: {stats['ignored']}</div>
        </div>
    """

    script_tag = """
        <script>
            function toggleRow(row, span) {
                let cells = row.getElementsByTagName('td');
                for (let i = 2; i < cells.length; i++) {
                    if (cells[i].style.display === 'none') {
                        cells[i].style.display = 'table-cell';
                        span.innerHTML = '[-]';
                    } else {
                        cells[i].style.display = 'none';
                        span.innerHTML = '[+]';
                    }    
                }
            }
            function expandAll() {
                let table = document.getElementById('comparisonTable');
                let tr = table.getElementsByTagName('tr');

                for (let i = 0; i < tr.length; i++) {
                    let icon = tr[i].getElementsByClassName('collapse-icon')[0];
                    if (icon) {
                        let cell = tr[i].getElementsByTagName('td')[2]
                        if (cell && cell.style.display === 'none') {
                            toggleRow(tr[i], icon);
                        }
                    }
                }
            }

            function collapseAll() {
                let table = document.getElementById('comparisonTable');
                let tr = table.getElementsByTagName('tr');

                for (let i = 0; i < tr.length; i++) {
                    let icon = tr[i].getElementsByClassName('collapse-icon')[0];
                    if (icon) {
                        let cell = tr[i].getElementsByTagName('td')[2]
                        if (cell && cell.style.display !== 'none') {
                            toggleRow(tr[i], icon);
                        }
                    }
                }
            }
        </script>
    """

    html_output = style + stats_div + search_bar + table_header + "\n".join(table_rows) + table_footer + script_tag

    with open(output_file, 'w') as f:
        f.write(html_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Compare two directories and generate an HTML report',
        usage='python compare_directories.py path/to/first/directory path/to/second/directory -i war jar -o my_differences.html'
    )
    parser.add_argument('dir1', help='Path to the first directory.')
    parser.add_argument('dir2', help='Path to the second directory.')
    parser.add_argument('-o', '--output', default='differences.html', help='Path to the output file (default: differences.html).')
    parser.add_argument('-i', '--ignore', nargs='+', default=['war', 'jar'], help='List of file extensions to ignore (default: war jar).')

    args = parser.parse_args()

    # get the start time
    st = time.time()
    compare_dirs(args.dir1, args.dir2, args.output, ignore_file_extensions=args.ignore)
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    print('Execution time:', elapsed_time, 'seconds')
