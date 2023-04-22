import re
with open(r'C:\Users\pdumas\Documents\SAP\SAP GUI\numpy0input1.txt','r') as f0:#see below comment
    read0=f0.read()
print(read0)
#whatever is in the file above must match this format below (usually just the '''for...''' loop results of '''convertInputRaw(GridTrials)ToInputFinal0.py''') e.g.
# for path_or_buf0 in [jsonString0]:
#     for orient0 in [None,'columns','index','split','records','values','table']:
#         for typ0 in ['frame','series']:
#             for dtype0 in [None,True,False,{'col3':'Float64'}]:
#                 for convert_axes0 in [None,True,False]:
#                     for convert_dates0 in [True,['col16'],False]:
#                         for date_unit0 in ['ms','s','us','ns']:
#                             for keep_default_dates0 in [True,False]:
#                                 for precise_float0 in [False,True]:
#                                     for encoding0 in ['utf-8','iso-8859-1']:
#                                         for encoding_errors0 in ['strict','backslashreplace','ignore']:
#                                             for compression0 in ['infer','gzip',{'method':'gzip','compressionlevel':'4','mtime':3}]:
#                                                 for storage_options0 in [None,{'s3':{'anon':True}}]:
#                                                     for lines0 in [False,True]:
#                                                         for chunksize0 in [None,4]:
#                                                             for nrows0 in [None,]3:
#                                                                 for engine0 in ['ujson','pyarrow']:
#                                                                     for dtype_backend0 in ['numpy_nullable','pyarrow']:
read0=re.sub('.*for ','',read0)#making part before equals
read0=re.sub(' in \[','=',read0)#making equals
read0=re.sub(',.*','',read0)#making part after equals
print(read0)#printing final result / all default values (e.g. kwarg0=value0\nkwarg1=value1\n...)
#python "C:\Users\pdumas\Downloads\Github\pythonTesting0\convertNumpyInputRaw(GridTrials)ToInputFinal.ForKwargInVals.To.KwargEqualsVal.Default0.py"