import os
import filecmp
import time
import html
import argparse
import hashlib
import csv

from difflib import SequenceMatcher
from difflib import Differ

class UnifiedDiffer(Differ):
    def unified_diff(self, a, b, fromfile='', tofile='', fromfiledate='',
                 tofiledate='', n=3, lineterm='\n'):
        r"""
        Compare two sequences of lines; generate the resulting delta, in unified
        format

        Each sequence must contain individual single-line strings ending with
        newlines. Such sequences can be obtained from the `readlines()` method
        of file-like objects.  The delta generated also consists of newline-
        terminated strings, ready to be printed as-is via the writeline()
        method of a file-like object.

        Example:

        >>> print ''.join(Differ().unified_diff('one\ntwo\nthree\n'.splitlines(1),
        ...                                'ore\ntree\nemu\n'.splitlines(1)),
        ...                                'old.txt', 'new.txt', 'old-date', 'new-date'),
        --- old.txt    old-date
        +++ new.txt    new-date
        @@ -1,5 +1,5 @@
          context1
        - one
        ?  ^
        + ore
        ?  ^
        - two
        - three
        ?  -
        + tree
        + emu
          context2
        """

        started = False
        for group in SequenceMatcher(None,a,b).get_grouped_opcodes(n):
            if not started:
                fromdate = '\t%s' % fromfiledate if fromfiledate else ''
                todate = '\t%s' % tofiledate if tofiledate else ''
                yield '--- %s%s%s' % (fromfile, fromdate, lineterm)
                yield '+++ %s%s%s' % (tofile, todate, lineterm)
                started = True
            i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
            yield "@@ -%d,%d +%d,%d @@%s" % (i1+1, i2-i1, j1+1, j2-j1, lineterm)
            for tag, i1, i2, j1, j2 in group:
                if tag == 'replace':
                    for line in a[i1:i2]:
                        g = self._fancy_replace(a, i1, i2, b, j1, j2)
                elif tag == 'equal':
                    for line in a[i1:i2]:
                        g = self._dump(' ', a, i1, i2)
                    if n > 0:
                        for line in g:
                            yield line
                    continue
                elif tag == 'delete':
                    for line in a[i1:i2]:
                        g = self._dump('-', a, i1, i2)
                elif tag == 'insert':
                    for line in b[j1:j2]:
                        g = self._dump('+', b, j1, j2)
                else:
                    raise ValueError

                for line in g:
                    yield line


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

def merge_str_diff(str, cdiff):
    result = ''
    for i in range(len(str)):
        if i >= len(cdiff):
            result += html.escape(str[i])
        elif cdiff[i] == ' ':
            result += html.escape(str[i])
        elif cdiff[i] == '+':
            result += '<span style="color: white; background-color: green">' + html.escape(str[i]) + '</span>'
        elif cdiff[i] == '-':
            result += '<span style="color: white; background-color: red">' + html.escape(str[i]) + '</span>'
        elif cdiff[i] == '^':
            result += '<span style="background-color: yellow">' + html.escape(str[i]) + '</span>'
        else:
            result += html.escape(str[i])
    return result

def parse_tag_file_list(tag_file_list):
    tag_dict = {}
    for tag_file in tag_file_list:
        tag, file_list = tag_file.split(':')
        tag_dict[tag] = file_list.split(',')
    return tag_dict

def transform_file_tags_dict(tag_files_dict):
    file_tags_dict = {}
    for tag, files in tag_files_dict.items():
        for file in files:
            if file in file_tags_dict:
                file_tags_dict[file].append(tag)
            else:
                file_tags_dict[file] = [tag]
    return file_tags_dict

def generate_file_path_td(file_path, file_tags_dict):
    file_path_td = f"<td class='ten'><span class='content'>{file_path}</span></td>"
    tags = []
    for file_path_key, tag_list in file_tags_dict.items():
        if file_path_key in file_path:
            tags.extend(tag_list)
    file_tags = set()
    for tag in tags:
        file_tags.add(tag)

    if len(file_tags) > 0:
        file_tags_span_list = [f"<span class='tags'>{tag}</span>" for tag in file_tags]
        file_path_td = f"<td class='ten'><span class='content'>{file_path}</span>{''.join(file_tags_span_list)}</td>"
    
    return file_path_td

def compare_dirs(dir1, dir2, output_file, ignore_file_extensions=[], nlines=3, tags_csv=''):
    tag_files_dict = process_tags_csv(tags_csv)
    all_tags = set()
    for tag, file_list in tag_files_dict.items():
        all_tags.add(tag)
    
    file_tags_dict = transform_file_tags_dict(tag_files_dict)

    tag_buttons_html_list = [f"<button onclick='onfilterByTag(this, \"{tag}\")' class='stats-button tags'>{tag}</button>" for tag in all_tags]
    tags_filter_div = f"""
        <div id="tags-filter-div" style="display: flex; justify-content: space-around; align-items: center; margin: 10px 0px; padding: 0.75rem; border: solid 2px black;">
            <div style='padding: 10px; font-weight: bold; text-align: center;'>Tags Available</div>
            {''.join(tag_buttons_html_list)}
        </div>
    """ if len(all_tags) > 0 else ""

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
        button {
            cursor: pointer;
        }
        button:hover {
            filter: brightness(85%);
        }
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
        .tags {
            padding: 5px;
            border-radius: 5px;
            background: #4f0054e0;
            color: white;
        }
        .view-action-button {
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
            text-align: center;
            margin-right: 10px;
        }
        #searchInput {
            width: 97.5%;
            margin: 10px 0px;
            padding: 5px;
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
        .ten .tags {
            display: inline-block;
            margin-left: 10px;
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
    <div style="display: block; width: 47.5%">
        <div style="display: inline-block; width: 200px">Search by file path / extn:</div>
        <input type="text" id="searchInput" list="filePaths" onkeyup="filterRows()" placeholder="Enter your text here...">
        <datalist id="filePaths"></datalist>
    </div>
    """

    table_header = f"""
        <div style="display: flex; justify-content: space-between">
            <div style="display: flex; align-items: center; width: 300px">
                <button id="expandAllBtn" class="view-action-button" onclick="expandAll()">Expand All</button>
                <button id="collapseAllBtn" class="view-action-button" onclick="collapseAll()">Collapse All</button>
            </div>
            {search_bar}
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

            file_path_td = generate_file_path_td(file_path1, file_tags_dict)

            if not os.path.exists(file_path2):
                stats['removed'] += 1
                table_rows.append(f"<tr class='file-removed'><td class='small'></td>{file_path_td}<td class='twenty' colspan='2' style='text-align: center;'><span>Removed from '{dir2}'</span></td></tr>")
                continue
            
            if filecmp.cmp(file_path1, file_path2, shallow=False):
                stats['identical'] += 1
                table_rows.append(f"<tr class='file-no-change'><td class='small'></td>{file_path_td}<td class='twenty' colspan='2' style='text-align: center;'><span>No change</span></td></tr>")
            elif os.path.splitext(file_path1)[1][1:] in ignore_file_extensions:
                stats['ignored'] += 1
                table_rows.append(f"<tr class='file-ignored'><td class='small'></td>{file_path_td}<td class='twenty'><span>{get_file_properties_table(file_path1, show_md5_hash=True)}</span></td><td class='twenty'><span>{get_file_properties_table(file_path2, show_md5_hash=True)}</span></td></tr>")
            else:
                stats['changed'] += 1
                with open(file_path1, encoding='utf8') as f1, open(file_path2, encoding='utf8') as f2:
                    diff1, diff2 = [], []
                    diff = list(UnifiedDiffer().unified_diff(f1.readlines(), f2.readlines(), fromfile=file_path1, tofile=file_path2, lineterm='', n=nlines))
                    # diff = list(difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file_path1, tofile=file_path2, lineterm='', n=nlines)) 
                    last_change_line = None
                    for line in diff:
                        if line.startswith('---') or line.startswith('+++'):
                            pass
                        elif line.startswith('@@'):
                            diff1.append(f"<hr><span style='color: grey;'>&nbsp;{html.escape(line)}</span><br>")
                            diff2.append(f"<hr><span style='color: grey;'>&nbsp;{html.escape(line)}</span><br>")
                        elif line.startswith('+'):
                            last_change_line = line
                            diff1.append(f'{get_ruler_span()}<span class="unselectable">{html.escape(line[1:])}</span>')
                            diff2.append(f"{get_ruler_span(line[0], '#008000a0')}<span style='color: green;'>{html.escape(line[1:])}</span>")
                        elif line.startswith('-'):
                            last_change_line = line
                            diff1.append(f"{get_ruler_span(line[0], '#ff000080')}<span style='color: red;'>{html.escape(line[1:])}</span>")
                            diff2.append(f'{get_ruler_span()}<span class="unselectable">{html.escape(line[1:])}</span>')
                        elif line.startswith('?') and line[1:].strip() != '':
                            # only used for custom mode
                            if last_change_line[0] == '+':
                                diff2.pop()
                                diff2.append(f"{get_ruler_span(last_change_line[0], '#008000a0')}<span style='color: green;'>{merge_str_diff(last_change_line[1:], line[1:])}</span>")
                            elif last_change_line[0] == '-':
                                diff1.pop()
                                diff1.append(f"{get_ruler_span(last_change_line[0], '#ff000080')}<span style='color: red;'>{merge_str_diff(last_change_line[1:], line[1:])}</span>")
                        else:
                            text = f"{get_ruler_span('=')}{html.escape(line[1:])}"
                            diff1.append(text)
                            diff2.append(text)
                    table_rows.append(f"""
                    <tr class='file-changed'>
                        <td class='small'><span class="collapse-icon" onclick="toggleRow(this.parentElement.parentElement, this)" style="cursor:pointer;">[-]</span></td>
                        {file_path_td}
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

            file_path_td = generate_file_path_td(file_path2, file_tags_dict)

            if not os.path.exists(file_path1):
                stats['added'] += 1
                table_rows.append(f"<tr class='file-added'><td class='small'></td>{file_path_td}<td class='twenty' colspan='2' style='text-align: center;'><span>Added in '{dir2}'</span></td></tr>")

    table_footer = "</tbody></table>"

    stats['total'] = stats['identical'] + stats['changed'] + stats['added'] + stats['removed'] + stats['ignored']
    stats_div = f"""
        <div id="stats-div" style="display: flex; justify-content: space-around; align-items: center; margin: 10px 0px; padding: 0.75rem; border: solid 2px black;">
            <div style='padding: 10px; font-weight: bold; text-align: center;' id="visible-rows-stat" data-total="{stats['total']}">Total: {stats['total']}</div>
            <button onclick="onfilterByStats(this, 'file-changed')" class='stats-button file-changed'>Text changed: {stats['changed']}</button>
            <button onclick="onfilterByStats(this, 'file-ignored')" class='stats-button file-ignored'>Hash changed: {stats['ignored']}</button>
            <button onclick="onfilterByStats(this, 'file-added')" class='stats-button file-added'>Added: {stats['added']}</button>
            <button onclick="onfilterByStats(this, 'file-removed')" class='stats-button file-removed'>Removed: {stats['removed']}</button>
            <button onclick="onfilterByStats(this, 'file-no-change')" class='stats-button file-no-change'>Identical: {stats['identical']}</button>
        </div>
    """

    script_tag = """
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

            function getActiveTags() {
                let tagsFilterDiv = document.getElementById('tags-filter-div');
                if (!tagsFilterDiv) {
                    return [];
                }

                let buttons = tagsFilterDiv.getElementsByTagName('button');
                let activeClasses = [];
                for (let i = 0; i < buttons.length; i++) {
                    if (buttons[i].classList.contains('active')) {
                        activeClasses.push(buttons[i].textContent);
                    }
                }
                return activeClasses;
            }

            function getFilePathFromTableRow(tr) {
                const [expCollapseTd, filePathTd] = tr.getElementsByTagName('td');
                if (filePathTd) {
                    const [filePathSpan, tagsSpan] = filePathTd.getElementsByTagName('span');
                    return filePathSpan.textContent || filePathSpan.innerText;
                }
                return '';
            }

            function shouldShowRow(tr, activeStats, activeTags) {
                const showByStatsFilter = activeStats.length > 0 ? activeStats.includes(tr.classList[0]): true;

                const [expCollapseTd, filePathTd] = tr.getElementsByTagName('td');
                const [, ...tagsSpanList] = filePathTd.getElementsByTagName('span');
                const rowTags = tagsSpanList.map(span => span.textContent);
                const showByTagsFilter = activeTags.length > 0 ? activeTags.every(tag => rowTags.includes(tag)): true;

                return showByStatsFilter && showByTagsFilter;
            }

            function updateSuggestions(value, activeStats, activeTags) {
                let dataList = document.getElementById('filePaths');
                dataList.innerHTML = '';
                let table = document.getElementById('comparisonTable');
                let tr = document.querySelectorAll('#comparisonTable > tbody > tr');
                
                for (let i = 0; i < tr.length; i++) {
                    const showRowByFilter = shouldShowRow(tr[i], activeStats, activeTags)

                    let txtValue = getFilePathFromTableRow(tr[i]);
                    if (showRowByFilter && txtValue.toUpperCase().includes(value.toUpperCase())) {
                        let option = document.createElement('option');
                        option.value = txtValue.trim();
                        dataList.appendChild(option);
                    }
                }
            }
            function filterRows() {
                let input = document.getElementById('searchInput');
                let filterText = input.value.toUpperCase();
                let activeStats = getActiveStats();
                let activeTags = getActiveTags();

                let tr = document.querySelectorAll('#comparisonTable > tbody > tr');
                let visibleRowCount = 0;
                for (let i = 0; i < tr.length; i++) {
                
                    const showRowByFilter = shouldShowRow(tr[i], activeStats, activeTags)

                    let txtValue = getFilePathFromTableRow(tr[i]);
                    if (showRowByFilter && txtValue.toUpperCase().indexOf(filterText) > -1) {
                        tr[i].style.display = '';
                        visibleRowCount++;
                    } else {
                        tr[i].style.display = 'none';
                    }
                }

                if (input.value.length >= 3) {
                    updateSuggestions(input.value, activeStats, activeTags);
                }

                let visibleRowsStat = document.getElementById('visible-rows-stat');
                const totalRows = visibleRowsStat.getAttribute('data-total');
                visibleRowsStat.innerHTML = totalRows === visibleRowCount.toString() ? `Total: ${totalRows}` : `Total: ${totalRows} | Visible: ${visibleRowCount}`;
            }
            function onfilterByStats($this, className) {
                $this.classList.toggle('active')
                filterRows()
            }

            function onfilterByTag($this, tagName) {
                console.log(tagName)
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
                {tags_filter_div}
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

    return stats

def create_index_html(html_files, index):
    with open(index, 'w') as index_file:
        html_top = f"""
            <html>
                <head>
                    <title>Directory Comparison Index</title>
                </head>
            <body>
                <h1>Directory Comparison Index</h1>
                <hr>
                <div>Legend: C - Total, T - Text changed, H - Hash changed, A - Added, R - Removed, I - Identical</div>
                <br>
                <table border="1">
                    <tr>
                        <th>Old Dir</th>
                        <th>New Dir</th>
                        <th>Tags CSV</th>
                        <th>Stats</th>
                        <th>Diff HTML</th>
                    </tr>
        """

        html_table_rows = []
        # get all groups from html_files
        groups = set()
        for html_file in html_files:
            (dir1, dir2, stats, output, group, tags_csv) = html_file
            groups.add(group)
        # sort the groups
        groups = sorted(groups)

        # create a row for each group
        for gp in groups:
            html_table_rows.append(f"<tr><td colspan='6' style='text-align: left; padding: 5px; font-weight: bold;'>{gp}</td></tr>")
            
            # get all html_files in the group
            html_files_in_group = [html_file for html_file in html_files if html_file[4] == gp] # 4 is the index of group in html_file tuple

            # create a row for each html_file in the group
            for html_file in html_files_in_group:
                (dir1, dir2, stats, output, group, tags_csv) = html_file
                html_table_rows.append(f"""
                    <tr>
                        <td>{dir1}</td>
                        <td>{dir2}</td>
                        <td>{tags_csv or '-'}</td>
                        <td>
                            <div style='display: flex; justify-content: space-around'>
                                <div style='width: 65px; text-align: center'>C: {stats['total']}</div>
                                <div style='width: 65px; text-align: center'>T: {stats['changed']}</div>
                                <div style='width: 65px; text-align: center'>H: {stats['ignored']}</div>
                                <div style='width: 65px; text-align: center'>A: {stats['added']}</div>
                                <div style='width: 65px; text-align: center'>R: {stats['removed']}</div>
                                <div style='width: 65px; text-align: center'>I: {stats['identical']}</div>
                            </div>
                        </td>
                        <td><a href="{output}">{output}</a></td>
                    </tr>
                """)

        html_bottom = """
                </table>
            </body>
        </html>
        """
        index_file.write(html_top + ''.join(html_table_rows) + html_bottom)

def process_tags_csv(csv_file):
    tag_files_dict = {}

    if not os.path.exists(csv_file):
        return tag_files_dict

    with open(csv_file, newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        next(csv_reader) # Skip the first row (labels)
        for row in csv_reader:
            if len(row) != 2:
                raise ValueError('Invalid CSV format. Each row should have exactly 2 values: tag, file_path.')
            tag, file_path = row
            if tag in tag_files_dict:
                tag_files_dict[tag].append(file_path)
            else:
                tag_files_dict[tag] = [file_path]
    return tag_files_dict

def process_csv(csv_file, ignore_file_extensions=[], nlines=3, index='differences_index.html'):
    html_files = []
    with open(csv_file, newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        next(csv_reader)  # Skip the first row (labels)
        for row in csv_reader:
            dir1 = row[0].strip()
            dir2 = row[1].strip()
            output = row[2].strip()
            group = row[3].strip() if len(row) > 3 else ''
            tags_csv = row[4].strip() if len(row) > 4 else '' # optional

            if not dir1 or not dir2 or not output:
                raise ValueError('Invalid CSV format. dir1, dir2 and output are required')
            
            print(f'Comparing {dir1} and {dir2} and generating {output}')
            # get the start time
            st = time.time()
            stats = compare_dirs(dir1, dir2, output, ignore_file_extensions, nlines, tags_csv)
            # get the end time
            et = time.time()
            # get the execution time
            elapsed_time = et - st
            print(f'Execution time for {output}:', elapsed_time, 'seconds')
            html_files.append((dir1, dir2, stats, output, group, tags_csv))
    create_index_html(html_files, index)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Compare two directories and generate an HTML report. Provide either dir1 and dir2 or a CSV file with multiple sets of arguments (dir1, dir2, output).',
        usage='''
    ------------------------------------
    python compare_directories.py path/to/first/directory path/to/second/directory --hash war jar --tags-csv path/to/tags_csv1.csv -n 3 -o my_differences.html
        (or)
    python compare_directories.py --csv path/to/csv_file.csv --hash war jar -n 3 --index differences_index.html
    ------------------------------------
    CSV Format:
    dir1,dir2,output,group,tags_csv
    path/to/first/directory,path/to/second/directory,my_differences.html,group_name,path/to/tags_csv1.csv'''
    )
    parser.add_argument('--csv', help='Path to the CSV file containing multiple sets of arguments.')
    parser.add_argument('--index', default='differences_index.html', help='Path to the output file (default: differences_index.html).')
    parser.add_argument('dir1', nargs='?', help='Path to the first directory.')
    parser.add_argument('dir2', nargs='?', help='Path to the second directory.')
    parser.add_argument('-o', '--output', default='differences.html', help='Path to the output file (default: differences.html).')
    parser.add_argument('--hash', nargs='+', default=['war', 'jar', 'jks'], help='List of file extensions to do MD5 Hash Compare (default: war jar jks).')
    parser.add_argument('--tags-csv', default='', help='CSV File containing list of tags for matching file paths (default: '').')
    parser.add_argument('-n', '--nlines', type=int, default=3, help='Number of unchanged lines to show above and below diff (default: 3).')

    args = parser.parse_args()

    # get the start time
    tst = time.time()

    if args.csv:
        process_csv(args.csv, args.hash, args.nlines, args.index)
    else:
        if not args.dir1 or not args.dir2:
            parser.error("Following arguments are required: dir1, dir2")
        stats = compare_dirs(args.dir1, args.dir2, args.output, ignore_file_extensions=args.hash, nlines=args.nlines, tags_csv=args.tags_csv)
        print(stats)
    # get the end time
    tet = time.time()
    # get the execution time
    total_elapsed_time = tet - tst
    print('Total Execution time:', total_elapsed_time, 'seconds')
