# compare-directory
Compare two different directories and generate html report

## Example
Two directories with different versions as below:

![image](https://user-images.githubusercontent.com/8114921/235133696-a62d004f-b089-4804-9502-4ace6d4bf0f1.png)

Run the following script
```
py .\compare.py .\testdata\dir_v1 .\testdata\dir_v2 -o diff.html
```

This outputs `diff.html` as shown below:

![image](https://user-images.githubusercontent.com/8114921/235133157-dfa06158-6c7d-4cb6-8fda-a65c1a5f889a.png)

The output html has a searchable interface input to filter by matching files as below:

![compare_diffhtml](https://user-images.githubusercontent.com/8114921/235130991-5a55a0d9-3869-469e-b4e1-95877bf120a8.gif)
