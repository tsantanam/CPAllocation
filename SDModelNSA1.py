from docplex.cp.model import *
import pandas as pd

df = pd.read_csv('AggDataNew200wFeasEqtPtBTier.csv')
numStops1 = len(df['StopAbbr'].tolist())

# Updated to include accurate amenity need estimates
simmeseat_cost = 500
simmeseat_install_np_tc = 5500
simmeseat_install_sw = 700

bench_cost = 5000  # survey and design + bench kit
bench_install_sw = 1000  # installation cost on existing sidewalk
bench_install_np = 3000  # installation cost on new pad

shelter_cost = 13000  # survey and design + shelter kit
shelter_install_sw = 6000  # installation cost on existing sidewalk
shelter_install_np = 10000  # installation cost on new pad



poss1 = df['PossibiltyOfAmentity'].tolist()

tier2=[]
for i in range(0, numStops1):
    if poss1[i]==0:
        tier2.append(0)
    else:
        if df['BASE'].tolist()[i]=='DIRT' and df['Stop_Type'].tolist()[i] == 'Sign':
            tier2.append(1)
        elif df['Stop_Type'].tolist()[i]=='MARTA Bench' or df['Stop_Type'].tolist()[i]=='Other Bench' or df['Stop_Type'].tolist()[i]=='Simme Seat':
            tier2.append(3)
        elif (df['BASE'].tolist()[i] == 'CONC' and df['Stop_Type'].tolist()[i] == 'Sign'):
            tier2.append(2)
        elif (df['Stop_Type'].tolist()[i]=='MARTA Shelter' or df['Stop_Type'].tolist()[i]=='Other Shelter') and df['ADA_ACCESS'].tolist()[i]!='Y':
            tier2.append(4)
        elif (df['Stop_Type'].tolist()[i]=='MARTA Shelter' or df['Stop_Type'].tolist()[i]=='Other Shelter') and df['ADA_ACCESS'].tolist()[i]=='Y'or df['Stop_Type'].tolist()[i]=='Station':
            tier2.append(5)

# Calculating cost of needs for each stop

#sidewalk1 = df['SIDEWALK'].tolist()

# installing simmeseats
need1 = []  # installing simmeseats
for i in range(0, numStops1):
    if tier2[i] <= 2:
        if df['BASE'].tolist()[i] == 'CONC':
            ss_cost = simmeseat_cost + simmeseat_install_sw
        else:
            ss_cost = simmeseat_cost + simmeseat_install_np_tc
        need1.append(ss_cost)
    else:
        need1.append(0)

# installing seating
need2 = []  # installing bench

for i in range(0, numStops1):
    if tier2[i] >= 3:
        need2.append(0)

    else:
        if df['BASE'].tolist()[i] == 'CONC':
            y_a = bench_cost + bench_install_sw

        else:
            y_a = bench_cost + bench_install_np

        need2.append(y_a)


# installing shelter
need3 = []  # installing shelter

for i in range(0, numStops1):
    if tier2[i] >= 4:
        need3.append(0)
    else:
        if df['BASE'].tolist()[i] == 'CONC':
            y = shelter_cost + shelter_install_sw
        else:
            y = shelter_cost + shelter_install_np
        need3.append(y)


Stops1 = df['StopAbbr'].tolist()
ridership1 = df['Ons_Dec19'].tolist()


budget1 = 3000000

n1 = range(numStops1)




mdl = CpoModel(name='SDModel')
funding = mdl.integer_var_list(len(Stops1), 0, budget1)

mdl.add(mdl.maximize_static_lex([mdl.sum(mdl.greater_or_equal(mdl.element(funding,s),19000)for s in n1),mdl.sum(mdl.greater_or_equal(mdl.element(funding,s),6000)for s in n1),mdl.sum(mdl.greater_or_equal(mdl.element(funding,s),1200)for s in n1)]))
for s in n1:
    mdl.add(mdl.element(funding,s)<=mdl.element(need3,s))  # amount given to a stop is less than or equal to its need - UPDATE
for s in n1:
    mdl.add(
        mdl.logical_or(mdl.logical_or(mdl.element(funding, s) == mdl.element(need1, s), mdl.element(funding, s) == 0),
                       mdl.logical_or(mdl.element(funding, s) == mdl.element(need2, s),
                                      mdl.element(funding, s) == mdl.element(need3,
                                                                             s))))  # discrete allocation based on cost of each amenity needed at a stop - UPDATE
mdl.add(mdl.sum(funding) <= budget1)  # the total funding allocated is less than or equal to ATLDOT's budget

for s in n1:
    mdl.add(mdl.if_then(mdl.element(tier2, s) <= 0, mdl.element(funding,
                                                                          s) <= mdl.element(need1, s)))  # stops with scores less than the unsolvable score are given no funding or a simme seat
for s in n1:
    mdl.add(mdl.if_then(mdl.element(tier2, s) >= 4, mdl.element(funding,
                                                                      s) == 0))  # stops with scores greater than the perfect score are not given funding in this model

msol = mdl.solve(TimeLimit=10, SearchType='Restart')
if msol:
    print("Solution: ")
    print([msol[funding[s]] for s in n1]);
    #print([msol[nhfunding[s]] for s in nh]);
    print(sum([msol[funding[s]] for s in n1]))

    fincost=[msol[funding[s]] for s in n1]

    amenitytype=[]
    for s in n1:
        if fincost[s] == 19000 or fincost[s] == 23000:
            amenitytype.append("Shelter")
        if fincost[s] == 8000 or (fincost[s] == 6000 and df['BASE'].tolist()[s] == 'CONC' ):
            amenitytype.append("Bench")
        if fincost[s] == 1200 or (fincost[s] == 6000 and df['BASE'].tolist()[s] != 'CONC' ):
            amenitytype.append("Simme Seat")
        if fincost[s]==0:
            amenitytype.append('None')
    newscore = []
    for i in n1:
        if amenitytype[i] == 'Shelter' and df['ADA_ACCESS'].tolist()[i] != 'Y':
            newscore.append(4)
        if amenitytype[i] == 'Shelter' and df['ADA_ACCESS'].tolist()[i] == 'Y':
            newscore.append(5)
        if amenitytype[i] == 'Simme Seat' or amenitytype[i] == 'Bench':
            newscore.append(3)
        if amenitytype[i] == 'None':
            newscore.append(tier2[i])
    df2 = pd.DataFrame()
    df2['Stop_ID'] = Stops1
    df2['Funding']=[msol[funding[s]] for s in n1]
    df2['Amenity_Type']=amenitytype
    df2['Current Score']=tier2
    df2['New Score'] =newscore

    #df2.to_csv('output.csv')

else:
    print("No solution found\n")

