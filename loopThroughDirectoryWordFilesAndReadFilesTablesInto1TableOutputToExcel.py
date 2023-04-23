#source: combination of ChatGPT, stackoverflow.com, and God
#function: concatenates all tables in all Word documents in 1 folder  and  outputs into 1 massive Excel table
#tip: if you just change the dir_path and output_path at the top, rest 'just works'   (it will create a pickle file storing contents in your directory so you can easily access later if needed! it will also open up the 2 created files at the end for your ease!)
#tip.2: if you happen to get an error like 'does not support enumeration' around line 42, that means 1 or more of the tables in 1 or more Word documents (I've littered the code with print statements so you'll know right before failure which one it is) has a table that doesn't behave (I only had 1 out of 100+ tables so I just moved it to a temp Excel manually and pasted it manually into the final massive Excel after this code ran)
#system specs: Windows 10, python 3.10, pandas 1.5.3, pywin32 304
import os,time
import pandas as pd
import win32com.client as win32

# Set the directory path for the Word documents
# dir_path = r"C:\path\to\folder\containing\Word\documents"
dir_path = r"C:\Users\pablodumas\Downloads\All_.Words.20230421"#this contains all Word docs (can contain more, but will only pick up .docx and .doc files to process)
output_path0=r'C:\Users\pablodumas\Downloads\All_.Words.20230421.finalTable1.xlsx'#this is the final Excel to write to and open

# Initialize an empty list to hold the tables from each document
tables_list = []

# Loop through each file in the directory
for filename in os.listdir(dir_path):#typical
    # Check if the file is a Word document
    if filename.endswith(".docx") or filename.endswith(".doc"):#from above, will only pick up .docx and .doc files to process
        # Create a full path to the file
        filepath = os.path.join(dir_path, filename)
        print('filepath')
        print(filepath)
        if os.path.basename(filepath).startswith(r'~'):#omits temporary, hidden files, which love to cause errors, from further processing
            continue
        
        # Initialize a Word application object and open the document
        # word = win32.gencache.EnsureDispatch("Word.Application")#did NOT work as was waiting to respond and raised error due to block ?
        word = win32.DispatchEx("Word.Application")#so opened each Word in unique instance instead
        doc = word.Documents.Open(filepath)
        print('doc')
        print(doc)


        # Loop through each table in the document and convert it to a pandas DataFrame
        for i in range(1, doc.Tables.Count+1):
            tbl = doc.Tables(i)
            data = []
            keys = []
            num_cols = tbl.Columns.Count
            for row_idx, row in enumerate(tbl.Rows):
                # Check if the row contains vertically merged cells
                is_merged = True#we are going to treat EVERY cell as a merged cell (if it's not merged, great, nothing much happens; if it's merged, it will concatenate the contents to result in 1 cell)
                # If the row is merged, split it into multiple rows
                merged_data = []
                for cell_idx, cell in enumerate(row.Cells):
                    try:
                        merged_data.append(cell.Range.Text.strip())
                        if row_idx == 0:#if the row is 0 (usually this is where the column headers are), then treat them as headers by appending them to keys
                            keys.append(cell.Range.Text.strip())
                    except:
                        merged_data[-1] += "\n" + cell.Range.Text.strip()#if causes error (which means vertically-merging), then concatenate the string with new lines (isn't try...except so great!)
                # If the merged row has too few columns, add empty cells to the end
                while len(merged_data) < num_cols:
                    merged_data.append("")
                data.append(merged_data)
            tbl_df = pd.DataFrame(data, columns=keys)
            print(tbl_df)
            print(tbl_df.columns)
            print(tbl_df.applymap(lambda x:str(x).replace('\r','').replace('\x07','').replace('\x0B','')))#in my example, there were a lot of no-no characters (e.g. \r,\x07,\x0B which are carriageReturn,bell,verticalTab) that Excel throws error if writing them so replaced in data with ''   (this and the below 'replace' you may have to tweak if you still have left over characters; .csv and VS Code are your friends (write to .csv, copy output to VS Code new file, it should highlight in bright red what are naughty characters!))
            tbl_df=tbl_df.applymap(lambda x:str(x).replace('\r','').replace('\x07','').replace('\x0B',''))
            print(tbl_df.columns.str.replace('\r','').str.replace('\x07','').str.replace('\x0B',''))#same as above, but replacing in columns
            tbl_df.columns=tbl_df.columns.str.replace('\r','').str.replace('\x07','').str.replace('\x0B','')
            tbl_df['sourceFile0']=os.path.basename(filename)#adding which Word doc the particular pandas.DataFrame data came from (so when it ends up in 1 massive Excel, you can tell which came from where)

            # Append the DataFrame to the list
            tables_list.append(tbl_df)


        # Close the document and Word application
        doc.Close()
        word.Quit()

# Concatenate all the tables into a single DataFrame
combined_df = pd.concat(tables_list, ignore_index=True)
pathOfThisFileThatIsRunningRightHere0=os.path.abspath(__file__)
pickleDumpPath0=pathOfThisFileThatIsRunningRightHere0+time.strftime('%Y%m%d')+'.2.pickle'
combined_df.to_pickle(pickleDumpPath0)
print('combined_df')
print(combined_df)
print(combined_df.applymap(lambda x:str(x).encode('ascii','ignore').decode('ascii')))#similar to above, getting rid of non-ascii characters since Excel doesn't like some non-ascii characters / throws an error when writing
combined_df=combined_df.applymap(lambda x:str(x).encode('ascii','ignore').decode('ascii'))
combined_df=combined_df.drop_duplicates()#don't want duplicates in data (especially since the data I was working with placed the headers in the actual data sometimes!)
print('pickleDumpPath0')
print(pickleDumpPath0)

# Write the DataFrame to an Excel file
output_path1=output_path0+'.csv'#test in .csv (since .csv can handle some characters Excel can't)
combined_df.to_csv(output_path1, index=False)
os.startfile(output_path1)#open up .csv
combined_df.to_excel(output_path0, index=False)#final Excel
os.startfile(output_path0)#open up Excel

#py -3.10 "C:\Users\pablodumas\Documents\Code\loopThroughDirectoryWordFilesAndReadFilesTablesInto1TableOutputToExcel.redacted.py"