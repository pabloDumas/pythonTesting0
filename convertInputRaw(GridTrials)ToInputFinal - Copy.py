import re
with open(r'C:\Users\pdumas\Documents\SAP\SAP GUI\numpy0input0.txt','r') as f0:#see below comment
    read0=f0.read()
print(read0)
# read0=r'n_samples,n_features,n_informative,n_targets,bias,effective_rank,tail_strength,random_state,coef,noise,shuffle,'#whatever is in the file above must match this format (usually just all the [kw]args for the function
read1=read0#copies to use later
read2=read0
read0=re.sub('^','for ',read0)
for i in list(range(read0.count(','))):#making grid format (e.g. for... for... for...)
    indents0=(' '*((i+1)*4))
    read0=re.sub('(\w+),',('\g<1>0 in [,]:\r\n'+indents0+'for '),read0,count=1)
print(read0)#printing grid format to use
read1=re.sub('(\w+),','f\'\g<1> {\g<1>0}\',',read1)
read1='print('+read1+'''sep='\\n\')'''
print(read1)#printing printKwargAndValues to include in grid (after last 'for...')
read2=re.sub('(\w+),','\g<1>=\g<1>0,',read2)
print(read2)#printing printFunctionCallWithKwargAndValues to include in grid (after last 'for...')
#python "C:\Users\pdumas\Downloads\Github\pythonTesting0\convertInputRaw(GridTrials)ToInputFinal.py"#call for pasting into cmd.exe or equivalent for quick running of this script
