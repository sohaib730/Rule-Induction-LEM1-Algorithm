__Author__="Sohaib Kiani"
## Rule Set for Numerical and Symbolic attributes using LEM1 Algorithm

import pandas as pd
import numpy as np
import math

class LERSdat:
    def __init__(self, filename=None):
        self.attributes = []            ###Holds name of all attribute types
        self.attributeTypes = []        ###Holds attribute types
        self.records = {}               ###Holds all data set
        self.index = {}         
        self.decision = ""          
        self.decisions = {}
        self.blocks = {}

        if filename is not None:
            self.open(filename)


    def open(self, filename):
        self.attributes = []
        self.attributeTypes = []
        self.records = {}
        self.index = {}
        self.decision = ""
        self.decisions = {}
        self.blocks = {}

        self.parse(filename)
        self.computeAllBlocks()
    def fileLineCount(self,filename):
        with open(filename) as f:
            num_lines = sum(1 for line in f)
        return num_lines
    def isnum(self,s):
        if s is None:
            return False
        try:
            float(s)
            return True
        except ValueError:
            return False
    def parse(self, filename):
        # parses the file to extract the dataset
        # file must be in LERS format
        linecount = self.fileLineCount(filename)
        phase = "find attributes"

        file = open(filename, 'r')
        case = 0
        attribute = 0
        caseValues = []

        print("Loading from file {}".format(filename))
        for linecurrent, line in enumerate(file):
            

            line = line.split()
            if not line:
                continue

            elif phase == "find attributes" and line[0].startswith("["):
                # this mode finds the attributes
                # attributes should be the second line in the file
                if line[-1].endswith("]"):
                    # if the line also ends the attributes, move to next step
                    self.attributes = line[1:-2]
                    self.decision = line[-2]

                    self.records = pd.DataFrame(columns = self.attributes + [self.decision])

                    # set up voting for numerical attribute types
                    self.attributeTypes = [0 for x in self.attributes]
                    phase = "read records"
                else:
                    # otherwise, keep reading attributes
                    phase = "reading attributes"
                    line = line[1:]

            elif phase == "reading attributes":
                # keep reading attributes
                if line[-1].endswith("]"):
                    # we found the end of the attribute list
                    self.attributes += line[:-2]
                    self.decision = line[-2]

                    self.records = pd.DataFrame(columns = self.attributes + [self.decision])

                    # set up voting for numerical attribute types
                    self.attributeTypes = [0 for x in self.attributes]
                    phase = "read records"
                else:
                    # we're still looking for attributes
                    self.attributes += line

            elif phase == "read records":
                # we finished reading attributes and now we're reading values for cases
                for element in line:
                    # TODO: (optimization) if isnum(element), element = float(element)

                    if element.startswith("!"):
                        # ingore the rest of the line.  it's a comment
                        break


                    if attribute + 1 > len(self.attributes):
                        # we've found all the attributes for this case

                        if self.decision not in self.index:
                            self.index[self.decision] = {}
                        if element not in self.index[self.decision]:
                            self.index[self.decision][element] = []

                        self.index[self.decision][element].append(case)

                        self.decisions[case] = element

                        caseValues.append(element)
                        # vote on if the attribute is a number or not
                        if len(self.attributeTypes) < len(caseValues):
                            self.attributeTypes.append(int(self.isnum(element)))
                        else:
                            self.attributeTypes[len(caseValues) - 1] += int(self.isnum(element))

                        self.records.loc[case] = caseValues

                        case += 1
                        attribute = 0
                        caseValues = []
                        continue

                    caseValues.append(element)
                    # vote on if the attribute is a number or not
                    self.attributeTypes[len(caseValues) - 1] += int(self.isnum(element))

                    if self.attributes[attribute] not in self.index:
                        self.index[self.attributes[attribute]] = {}
                    if element not in self.index[self.attributes[attribute]]:
                        self.index[self.attributes[attribute]][element] = set([])
                    self.index[self.attributes[attribute]][element].add(case)

                    attribute += 1

        # determine if attribute was numerical
        # todo: (optimization) base numerical decision on what values are, not how many can convert to float

        numcases = len(self.records.columns)
        tempHeader = self.attributes + [self.decision]
        tempAttributeTypes = self.attributeTypes
        self.attributeTypes = {}

        for i in range(len(tempAttributeTypes)):
            if len(set(self.records[(self.attributes + [self.decision])[i]])) == 2:
                self.attributeTypes[tempHeader[i]] = "Binary"
            elif tempAttributeTypes[i] > numcases / 2:
                self.attributeTypes[tempHeader[i]] = "Numerical"
            else:
                self.attributeTypes[tempHeader[i]] = "Discrete"
        print("\n")



    def computeAllBlocks(self):
        for attr in (self.attributes + [self.decision]):
            self.blocks[attr] = {}

        
        self.computeNumericalBlocks()
        
        self.computeDiscreteBlocks()

        # add all the "do-not-care" cases to the blocks for that attribute
        for attr in self.attributes:
            if "*" in self.blocks[attr]:
                for val in self.blocks[attr]:
                    if val not in ["*", "?", "-"]:
                        self.blocks[attr][val] = self.blocks[attr][val].union(self.blocks[attr]["*"])


    def computeNumericalBlocks(self):
        total = len(self.attributes + [self.decision])
        for idx, attribute in enumerate(self.attributes + [self.decision]):
            
            if self.attributeTypes[attribute] == "Numerical":
                # find all unique values
                values = sorted(set(self.records[attribute]).difference(set(["*", "?", "-"])), key=lambda item: float(item))
                
                # compute the cutpoints for this attribute
                cutpoints = []
                for i in range(len(values)-1):
                    cutpoints.append((float(values[i])+float(values[i+1])) / 2)

                
                # for each cut point, compute the <= and the > blocks
                for cutpoint in cutpoints:
                    self.blocks[attribute][">{}".format(cutpoint)] = set()
                    self.blocks[attribute]["<={}".format(cutpoint)] = set()
                    for case in self.records.index:
                        if self.isnum(self.records[attribute][case]):
                            if float(self.records[attribute][case]) > cutpoint:
                                self.blocks[attribute][">{}".format(cutpoint)].add(case)
                            else:
                                self.blocks[attribute]["<={}".format(cutpoint)].add(case)

                # find the "do-not-care" block for numerical attributes, too!
                if "*" in self.index[attribute]:
                    self.blocks[attribute]["*"] = set(self.index[attribute]["*"])


    def computeDiscreteBlocks(self):
        total = len(self.attributes + [self.decision])
        for (idx, attribute) in enumerate(self.attributes + [self.decision]):
            
            if self.attributeTypes[attribute] != "Numerical":
                for value in self.index[attribute]:
                    self.blocks[attribute][value] = set(self.index[attribute][value])
        

    def __str__(self):
        # this class will display the index when it is printed
        retStr = ""
        retStr += "Decision:   '{}'\n".format(self.decision)
        retStr += "Attributes: {}\n".format(self.attributes)
        for attribute in self.attributes:
            retStr += str(attribute) + "\n"
            for value in self.index[attribute]:
                retStr += "\t{}: {}\n".format(value, self.index[attribute][value])

        retStr += "{}\n".format(self.decision)
        for value in self.index[self.decision]:
            retStr += "\t{}: {}\n".format(value,self.index[self.decision][value])

        return retStr
"""
def check_consistency(df1,d1):
    global_check='False'
    
    index=0
    count=0
    for row1 in df1.itertuples():
        
        temp=set()
        
        for row2 in df1.itertuples():
            if row1[1:-1]==row2[1:-1]:
                temp.add(row2[0])
                count=count+1
        check='False'
        for v in d1.keys():
            if temp.issubset(d1[v])==True :
                print temp
                check='True'
    
        if check=='False':
            global_check='True'
 
        if count==len(df1):
            print count
            break
    
    if global_check=='True':
        
        return 'True'
    else:
        return 'False'"""
        
def check_consistency_new(df1,d1):

    attr_len=len(df1)
    #window=1  ####when window become length terminate
    att_blocks={}
    
    for i in range(0,attr_len):
        temp=set()
    	row1=df1.iloc[i].values
    	temp.add(i)
        for k in range(i+1,attr_len):
            row2=df1.iloc[k].values
            check='True'
            for index in range(0,len(row1)-1):
                if (row1[index]!=row2[index]):
                    check='False'
            if check=='True':
                temp.add(k)
        att_blocks[i]=temp
    All_consistent='True'
    for i in att_blocks:
        block_consistent='False'
        for d in d1:
            
            if (att_blocks[i].issubset(d1[d])==True):
                block_consistent='True'
        if block_consistent=='False':   ####One Fails means all fail
            All_consistent='False'

    return All_consistent
A={}
def Attrib_set(df1):


    index=0
    count=0
    for row1 in df1.itertuples():
        
        temp=set()
        Repeat=False
        for row2 in df1.itertuples():
            che=set()
            che.add(row1[0])
            for c in A.keys():
                if che.issubset(A[c])==True:
                    Repeat=True
            if Repeat==True:
                break
            if row1[1:-1]==row2[1:-1]:
                temp.add(row2[0])
                count=count+1


    

        if Repeat==False:
            A[index]=temp
            index=index+1
        if count==len(df1):
            break

"""def LEM1(df2,dec_dict):
    attr_len=len(df2.attributes)
    #window=1  ####when window become length terminate
    df_col=pd.DataFrame()
    final_attr_list=[]
    
    for i in range(0,attr_len):
        
        comb={}
        for count in range(0,nCr(attr_len,i)):
            attr=[]
            window=i
            skip=1
            win=i
            while window > 0:
                window=window-1
                win=win-skip
                attr.append(df2.attributes[(count+win)%attr_len])
                if window==0:
                    for k in comb.keys():
                        if (attr==comb[k]):
                            
                                window=i
                                skip=skip+1
                                win=i
                                attr=[]
            comb[count]=attr
            #print comb.keys()
            df_col=df.drop(attr,1)
            #print df_col
            if check_consistency(df_col,dec_dict)=='False':
               
               
                final_attr_list=[]
                final_attr_list=list(df_col)


    return final_attr_list[:-1]"""
def LEM1_singleglobal(df2,dec_dict):
    attr_len=len(df2.attributes)
    #window=1  ####when window become length terminate
    P=df2.records
    
    for att in df2.attributes:
        
        Q=P.drop(att,1)
        if check_consistency_new(Q,dec_dict)=='True':
            
            P=Q
    
    R=P.columns
    		
    return R[:-1]
def nCr(n,r):
    f = math.factorial
    return f(n) / f(r) / f(n-r)
if __name__ == "__main__":
    IP_filename = raw_input("Please enter full input File Name:  ")
    OP_filename = raw_input("Please enter Output File Name without extension:  ")
    
    o = LERSdat(IP_filename)
    file_cert=open(OP_filename+'-certain.txt', 'w') 
    file_poss=open(OP_filename+'-possible.txt','w')

    
    row_size=len(o.records.index)
    U=set(range(0,len(o.records.index)))
    temp_col=pd.Series(np.random.randn(row_size))
    new_attribute_list=[]
    
    for att in o.attributes:
        if (o.attributeTypes[att]=='Numerical'):
            o.records=o.records.drop(att,axis=1)
            for cutpoints in o.blocks[att]:
                if (cutpoints[0]=='>'):
                    low_set=set()
                    low_set=U-o.blocks[att][cutpoints]
                    for index in o.blocks[att][cutpoints]:
                        temp_col[index]='H'
                    for index in low_set:
                        temp_col[index]='L'
                    col_name=str(att)+'_'+cutpoints[1:]
                    o.records[col_name]=temp_col
                    new_attribute_list.append(col_name)
        else:
            new_attribute_list.append(att)
    o.attributes=new_attribute_list

    decision=o.records[o.decision]
    o.records=o.records.drop(o.decision,1)
    o.records[o.decision]=decision
    print "Dicretized DataSet"
    print o.records
    df=o.records
    if check_consistency_new(df,o.blocks[o.decision])=='False':
        print('DataSet Not Consistent')
       
    else:
        print('Dataset Consistent')
        file_poss.write("! Possible rule set is not shown since it is identical with the certain rule set")
        

    
    
    Attrib_set(df)   ####A is global data Frame, set by this function
    #print(A)
    decision_all_sets={}
    #####Upper and Lower Approx
    for se in o.blocks[o.decision]:
        dset=o.blocks[o.decision][se]
        upper_approx=set()
        lower_approx=set()
        for att_key in A:
            for x in A[att_key]:
                t=x in dset
                if (t == True):
                    upper_approx=upper_approx.union(A[att_key])
                    if (A[att_key].issubset(dset)==True):
                        lower_approx=lower_approx.union(A[att_key])

        decision_all_sets[o.decision+','+se+'^lower']=lower_approx
        decision_all_sets[o.decision+','+se+'^upper']=upper_approx


##Print LEM1 Algorithm to find Global Covering
                
    print decision_all_sets
    rule_list=[]

    for ke in decision_all_sets:
            rule_type=1
            rule_df={}
            test={}
            ind=ke.find('^')+1
            if ke[ind:]=='upper':
                rule_type=0
                if (decision_all_sets[ke[:ind]+'lower']==decision_all_sets[ke]):
                    continue
                else:
                    print ("Possible Rule Set:")
            else:
                print ("Certain Rule Set:")
            test={}
            test[0]=decision_all_sets[ke]
            test[1]=U-decision_all_sets[ke]
            glob=LEM1_singleglobal(o,test)
            print ('Global Covering for Decision:',ke+'_Approximation')
            print (glob)
            ignore_list=[]
            rule_df_records={}
            
            for x in test[0]:
                local_rule_list=[]
                priority_rule=[]
                ignore=False
                for ignore_check in ignore_list:
                    if x==ignore_check:
                        ignore=True
                        break
                if (ignore==True):
                    continue
                for att in glob:
                        local_rule_list.append('('+att+','+o.records[att][x]+')')
                        
                        ind1=0
                        
                        temp_set=set()
                        for elem in df[att]:
                            if (elem==df[att][x]):
                                #rule_df_records[att]=elem
                                
                                temp_set.add(ind1)
                            ind1=ind1+1
                        rule_df[att]=temp_set

#print (rule_df_records)
                local_glob=[]
                local_glob=glob
                comb=[]

                ###Doing elimination on Rule set
                for i in range(0,int(math.pow(2,len(rule_df)))):
                    comb.append(['0']*len(rule_df))
                ###Generating all possible combinations of attribute in rule set
                le=len(rule_df)
                for i in range(0,int(math.pow(2,len(rule_df)))):
                    bin=list('{0:0b}'.format(i))
                    ind2=len(rule_df)-1
                    k=len(bin)-1
                    while k>=0:
                        
                        comb[i][ind2]=bin[k]
                        ind2=ind2-1
                        k=k-1

                case_cover=[]
                case_cover.append(x)   ####Cases covered by Rule Set
                rule_elem_set=set()

                for i in range(0,len(comb)):
                    
                    rule_elem_set=U

                    sel=0
                    for key in rule_df:
                        if comb[i][sel]=='1':
                            rule_elem_set=rule_elem_set & rule_df[key]
                        sel=sel+1
                    sel=0
                   
                    if (rule_elem_set.issubset(test[0])):
                        local_glob=[]
                        for key in rule_df:
                            if comb[i][sel]=='1':
                               
                                priority_rule.append('('+key+','+o.records[key][x]+')')                         ###Attribute Name
                                
                                
                                local_glob.append(key)
                            sel=sel+1
                    
                        break
                for j in test[0]:
                    if (x!=j):
                        
                        if (o.records.loc[x,local_glob].equals(o.records.loc[j,local_glob])==True):
                            ignore_list.append(j)
                            case_cover.append(j)
                if not priority_rule:
                    rule_list.append(local_rule_list)
                    print (str(local_rule_list)+"--->"+'('+str(ke[:ind-1])+')')
                    if rule_type == 1:
                        file_cert.write(str(local_rule_list)+"   --->   "+'('+str(ke[:ind-1])+')'+'\n\n')
                    else:
                        file_poss.write(str(local_rule_list)+"  --->  "+'('+str(ke[:ind-1])+')'+'\n\n')
                else:
                    rule_list.append(priority_rule)
                    print (str(priority_rule)+"--->"+'('+str(ke[:ind-1])+')')
                    if rule_type==1:
                        file_cert.write(str(priority_rule)+"   --->   "+'('+str(ke[:ind-1])+')'+'\n\n')
                    else:
                        file_poss.write(str(priority_rule)+"   --->   "+'('+str(ke[:ind-1])+')'+'\n\n')
                rule_list.append(ke[:ind-1])
                print ("Cases Cover:",case_cover)
#print rule_list
    file_cert.close()
    file_poss.close()
    #for i in o.records['Hair']:
#print i
#for attr in o.attributes + [o.decision]:
#       print("{}:{}".format(attr,o.blocks[attr]))
    #print(o)
