import os
import filecmp
import difflib
import time
import html
import argparse
import hashlib

def get_ruler_span(ruler = '&nbsp;', color = '#8080808a'):
    return f"""
        <div style='color: {color}; display: inline-flex; width: 20px; margin-right: 5px; justify-content: center'>
            &nbsp;{ruler}&nbsp;
        </div>
    """
def get_file_properties_table(file_path, show_md5_hash = False):
    md5_hash_tr = f"""
        <tr>
            <td>MD5 Hash</td>
            <td>{hashlib.md5(open(file_path,'rb').read()).hexdigest()}</td>
        </tr>
    """ if show_md5_hash else ""

    return f"""
        <table class='no-border'>
            <tr>
                <td>File size</td>
                <td>{sizeof_fmt(os.path.getsize(file_path))}</td>
            </tr>
            <tr>
                <td>Last modified time</td>
                <td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(file_path)))}</td>
            </tr>
            {md5_hash_tr}
        </table>
    """

def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.000:
            return f"{num:3.3f}{unit}{suffix}"
        num /= 1024.000
    return f"{num:.1f}Yi{suffix}"

def compare_dirs(dir1, dir2, output_file, ignore_file_extensions=[], nlines=3):
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
        .stats-button {
            padding: 10px; 
            border-radius: 5px; 
            font-weight: bold; 
            text-align: center;
        }
        .stats-button.active {
            filter: brightness(75%);
            border: solid 3px rgba(0, 0, 244, 0.7);
            box-shadow: rgba(0, 0, 0, 0.02) 0px 1px 3px 0px, rgba(27, 31, 35, 0.15) 0px 0px 0px 1px;
        }
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
            background: #fff;
        }
        .small {
            width: 2rem;
            vertical-align: top;
            text-align: center;
        }
        .ten {
            vertical-align: top;
        }
        .twenty {
            width: 37.5%;
            vertical-align: top;
        }
        table.no-border td {
            border: none;
        }
        td {
            border: solid;
            word-wrap:break-word
        }

        .file-changed {
            background: #ffffff;
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
    <div style="display: inline-block;">Search by file path / extn:</div>
    <input type="text" id="searchInput" list="filePaths" onkeyup="filterRows()" placeholder="Enter your text here...">
    <datalist id="filePaths"></datalist>
    <script>
        function getActiveStats() {
            let statsDiv = document.getElementById('stats-div');
            let buttons = statsDiv.getElementsByTagName('button');
            let activeClasses = [];
            for (let i = 0; i < buttons.length; i++) {
                if (buttons[i].classList.contains('active')) {
                    activeClasses.push(buttons[i].classList[1]);
                }
            }
            return activeClasses;
        }

        function updateSuggestions(value, activeStats) {
            let dataList = document.getElementById('filePaths');
            dataList.innerHTML = '';
            let table = document.getElementById('comparisonTable');
            let tr = document.querySelectorAll('#comparisonTable > tbody > tr');
            
            for (let i = 0; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName('td')[1];
                let showByStatsFilter = activeStats.length > 0 ? activeStats.includes(tr[i].classList[0]): true;
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (showByStatsFilter && txtValue.toUpperCase().includes(value.toUpperCase())) {
                        let option = document.createElement('option');
                        option.value = txtValue.trim();
                        dataList.appendChild(option);
                    }
                }
            }
        }
        function filterRows() {
            let input = document.getElementById('searchInput');
            let filterText = input.value.toUpperCase();
            let activeStats = getActiveStats();

            let tr = document.querySelectorAll('#comparisonTable > tbody > tr');

            for (let i = 0; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName('td')[1];
                let showByStatsFilter = activeStats.length > 0 ? activeStats.includes(tr[i].classList[0]): true;
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (showByStatsFilter && txtValue.toUpperCase().indexOf(filterText) > -1) {
                        tr[i].style.display = '';
                    } else {
                        tr[i].style.display = 'none';
                    }
                }
            }

            if (input.value.length >= 3) {
                updateSuggestions(input.value, activeStats);
            }
        }
    </script>
    """

    table_header = f"""
        <div>
            <button id="expandAllBtn" onclick="expandAll()">Expand All</button>
            <button id="collapseAllBtn" onclick="collapseAll()">Collapse All</button>
        </div>
        <br>
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
            
            if filecmp.cmp(file_path1, file_path2, shallow=False):
                stats['identical'] += 1
                table_rows.append(f"<tr class='file-no-change'><td class='small'></td><td class='ten'>{file_path1}</td><td class='twenty' colspan='2' style='text-align: center;'><span>No change</span></td></tr>")
            elif os.path.splitext(file_path1)[1][1:] in ignore_file_extensions:
                stats['ignored'] += 1
                table_rows.append(f"<tr class='file-ignored'><td class='small'></td><td class='ten'>{file_path1}</td><td class='twenty'><span>{get_file_properties_table(file_path1, show_md5_hash=True)}</span></td><td class='twenty'><span>{get_file_properties_table(file_path2, show_md5_hash=True)}</span></td></tr>")
            else:
                stats['changed'] += 1
                with open(file_path1, encoding='utf8') as f1, open(file_path2, encoding='utf8') as f2:
                    diff1, diff2 = [], []
                    diff = list(difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file_path1, tofile=file_path2, lineterm='', n=nlines))
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
                    <tr class='file-changed'>
                        <td class='small'><span class="collapse-icon" onclick="toggleRow(this.parentElement.parentElement, this)" style="cursor:pointer;">[-]</span></td>
                        <td class='ten'>{file_path1}</td>
                        <td class='twenty'>
                            {get_file_properties_table(file_path1)}
                            {'<br>'.join(diff1)}
                        </td>
                        <td class='twenty'>
                            {get_file_properties_table(file_path2)}
                            {'<br>'.join(diff2)}
                        </td>
                    </tr>
                    """)

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
        <div id="stats-div" style="display: flex; justify-content: space-around; align-items: center; margin: 10px 0px; padding: 0.75rem; border: solid 2px black;">
            <div style='padding: 10px; font-weight: bold; text-align: center;'>Total: {stats['total']}</div>
            <button onclick="onfilterByStats(this, 'file-changed')" class='stats-button file-changed'>Text changed: {stats['changed']}</button>
            <button onclick="onfilterByStats(this, 'file-ignored')" class='stats-button file-ignored'>Hash changed: {stats['ignored']}</button>
            <button onclick="onfilterByStats(this, 'file-added')" class='stats-button file-added'>Added: {stats['added']}</button>
            <button onclick="onfilterByStats(this, 'file-removed')" class='stats-button file-removed'>Removed: {stats['removed']}</button>
            <button onclick="onfilterByStats(this, 'file-no-change')" class='stats-button file-no-change'>Identical: {stats['identical']}</button>
        </div>
    """

    script_tag = """
        <script>
            function onfilterByStats($this, className) {
                $this.classList.toggle('active')
                filterRows()
            }

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

    html_output = f"""
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>Directory Comparison Report</title>
                {style}
            </head>
            <body>
                <h1 style='text-align: center; width: 100%;'>Directory Comparison Report</h1>
                {stats_div}
                {search_bar}
                <hr>
                {table_header}
                {''.join(table_rows)}
                {table_footer}
                {script_tag}
            </body>
        </html>
    """

    with open(output_file, 'w') as f:
        f.write(html_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Compare two directories and generate an HTML report',
        usage='python compare_directories.py path/to/first/directory path/to/second/directory --hash war jar -o my_differences.html'
    )
    parser.add_argument('dir1', help='Path to the first directory.')
    parser.add_argument('dir2', help='Path to the second directory.')
    parser.add_argument('-o', '--output', default='differences.html', help='Path to the output file (default: differences.html).')
    parser.add_argument('--hash', nargs='+', default=['war', 'jar', 'jks'], help='List of file extensions to do MD5 Hash Compare (default: war jar jks).')
    parser.add_argument('-n', '--nlines', type=int, default=3, help='Number of unchanged lines to show above and below diff (default: 3).')

    args = parser.parse_args()

    # get the start time
    st = time.time()
    compare_dirs(args.dir1, args.dir2, args.output, ignore_file_extensions=args.hash, nlines=args.nlines)
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    print('Execution time:', elapsed_time, 'seconds')
