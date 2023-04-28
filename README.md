# compare-directory
Compare two different directories and generate html report

## Example
Two directories with different versions as below:

![image](https://user-images.githubusercontent.com/8114921/235129035-97f64dd0-2151-4280-8330-2f9687045871.png)

Run the following script
```
py .\compare.py .\testdata\dir_v1 .\testdata\dir_v2 -o diff.html
```

This outputs `diff.html` with searchable interface to see matching files as below:

![compare_diffhtml](https://user-images.githubusercontent.com/8114921/235130991-5a55a0d9-3869-469e-b4e1-95877bf120a8.gif)
