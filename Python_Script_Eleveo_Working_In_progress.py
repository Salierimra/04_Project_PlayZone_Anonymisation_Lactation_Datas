#Import librairies génériques

import subprocess
import sys

# Liste des packages à installer via pip (pour assurer que le code fonctionne peu importe la version de python)
required_packages = [
    "pandas",
    "ipywidgets",
    "numpy",
    "pandas" 
]

def install_packages(packages):
    for pkg in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except Exception as e:
            print(f"❌ Erreur lors de l'installation de {pkg} : {e}")

# Installation au lancement du script des packages manquants
install_packages(required_packages)

#import de toutes les librairies necessaires
import os
import sqlite3
from sqlite3 import IntegrityError

import time
import pandas as pd
from pathlib import Path
import gc
import ipywidgets as widgets
from IPython.display import display
import numpy as np
import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta
import random
from dateutil.relativedelta import relativedelta
from datetime import datetime

def Deleting_output_DB(path_db):
    
    '''
    This function will delete the file located at the path provided as input
        If the file does not exist -> we continue the code
        3 attempts to delete it to give Windows time to process the request
        If NOK after 3 attempts -> Go_on = False -> we stop the code
        If other error -> Go_on = False -> we stop the code
        If everything OK or file missing -> Go_on = True -> we continue the code
    '''

    Go_on = True # stay true as long as everything is ok
    print(f"2 - Deleting file : {path_db} in progress")
    
    #Case 1 : File not found
    if not os.path.exists(path_db):
        # First execution -> file not found
        print(f"File {path_db} not found, continuing execution")
        return Go_on #Go_on = True
  
    for tries in range(3):
        try:
           
           #Case 2 : File found and deleted without problem
            gc.collect() # call python garbage collector
            time.sleep(1)  # Wait 1 seconde to let windows processing
            os.remove(path_db)
            print(f"File {path_db} deleted with success after : {tries+1} tries)")
            return Go_on #Go_on = True
            
        except PermissionError:
            #Case 3 : File found but permission error (already open?)
            if tries < 2:
                print(f"Tries {tries+1} failed, next try...")
            else:
                print(f"Permission not granted after 3 attempts")
                print("The file is locked due to permission issues - the script cannot continue")
                print("Try restarting the Python kernel")
                print("Try closing any application that may be using the file (Visual Studio, DbBrowser, ...)")
                print(f"Try manually deleting the file {path_db}")
                Go_on = False #Go_on = False
                
        except Exception as e:
            #Case 4 : File found but unknown error
            print(f"An error occurs, ending script.... : {e}")
            Go_on = False #Go_on = False
            break
    
    return Go_on

def Creating_Out_DB(input_db,output_db):
    """
    Duplicate input DB structure towrds output DB    
    Args:
        input_db: input DB path
        output_db: output DB path
    """
    
    # Connecting DB + cursors creation
    src_conn = sqlite3.connect(input_db)
    tgt_conn = sqlite3.connect(output_db)
    
    src_cur = src_conn.cursor()
    tgt_cur = tgt_conn.cursor()
    Go_on =True
    
    try:
        # Recovering all SQL infos
        src_cur.execute("""
            SELECT sql 
            FROM sqlite_master 
            WHERE sql IS NOT NULL 
            AND type IN ('table', 'index', 'trigger', 'view')
            ORDER BY type DESC
        """)
        
        sql_statements = src_cur.fetchall()
        
        # Execute each statement in output DB
        for statement in sql_statements:
            sql = statement[0]
            if sql:  # not None
                tgt_cur.execute(sql)
        tgt_conn.commit()
        print(f"\n Databse '{output_db}' created !")
        
        # Afficher un résumé
        tgt_cur.execute("SELECT name, type FROM sqlite_master WHERE type='table'")
        tables = tgt_cur.fetchall()
        print(f"\n Tables created: {len(tables)}")
            
    except sqlite3.Error as e:
        print(f"An error occurs, stoping script : {e}")
        tgt_conn.rollback()
        Go_on =False

        
    finally:
        '''Closing DB connections'''
        src_conn.close()
        tgt_conn.close()
    return Go_on

def Data_type_consistency(dst_cur, dst_con):
    """
    Fixes DATE/DATETIME types to TEXT, regenerates tables with FK,
    and restores primary/foreign keys in accordance with the source database definitions.
    Compatible with SQLite 3.34 (no ALTER TABLE DROP COLUMN).
    """

    try:
        go_on = True

        # ============================================================
        #  CL_LAITEXPL (DATETIME)
        # ============================================================

        dst_cur.execute("""
            CREATE TABLE CL_LAITEXPL_new (
                ID_LAITEXPL         NUMERIC(7,0) PRIMARY KEY,
                NOINTEXPL           NUMERIC(11,0) NOT NULL
                                      REFERENCES EXPLOITATION(NOINTEXPL),
                DATE_CTRL           DATETIME NOT NULL,
                TRAIT1              TEXT(2),
                CD_TYPE_CTRL        NUMERIC(2) REFERENCES CL_AIDE_TYPE_CTRL(CD_TYPE_CTRL),
                DATE_RECEPT_ANALYSE DATETIME,
                CD_ETAPE_CTRL       NUMERIC(2,0) NOT NULL
                                      REFERENCES CL_AIDE_ETAPE_CTRL(CD_ETAPE_CTRL)
            );
        """)
        dst_cur.execute("DROP TABLE CL_LAITEXPL;")
        dst_cur.execute("ALTER TABLE CL_LAITEXPL_new RENAME TO CL_LAITEXPL;")

        
         # ============================================================
        # AIDACTIEL transform ACTIEL in VARCHAR(2) client mistake
        # ============================================================

        dst_cur.execute("""
            CREATE TABLE AIDACTIEL_new (
            ACTIEL VARCHAR(2) PRIMARY KEY,
            ACTIELINT TEXT(20),
            ABREV_INTERBULL TEXT(3),
            ACTIELTYPE TEXT(1),
            DMG NUMERIC(5,0),
            LAIT_MIN NUMERIC(4,0),
            LAIT_MAX NUMERIC(4,0),
            PC_MG_MIN NUMERIC(5,2),
            PC_MG_MAX NUMERIC(5,2),
            PC_PROT_MIN NUMERIC(5,2),
            PC_PROT_MAX NUMERIC(5,2)
        )
        """)
        # copy datas in new table
        dst_cur.execute("""
        INSERT INTO AIDACTIEL_new 
        SELECT * FROM AIDACTIEL;
        """)
        dst_cur.execute("DROP TABLE AIDACTIEL;")
        dst_cur.execute("ALTER TABLE AIDACTIEL_new RENAME TO AIDACTIEL;")

        # ============================================================
        # CL_LAITLACT (DATETIME DATE_VEL / DATE_TAR)
        # ============================================================

        dst_cur.execute("""
            CREATE TABLE CL_LAITLACT_new (
                ID_LAITLACT NUMERIC(7,0) PRIMARY KEY,
                NOAN        NUMERIC(11,0) REFERENCES IDENTANV(NOAN),
                NOLACT      NUMERIC(4,0) NOT NULL,
                DATE_VEL    DATETIME NOT NULL,
                DATE_TAR    DATETIME,
                LAIT        NUMERIC(8),
                MG          NUMERIC(8),
                PROT        NUMERIC(8),
                LAIT305     NUMERIC(8),
                MG305       NUMERIC(8),
                PROT305     NUMERIC(8),
                LAIT365     NUMERIC(8),
                MG365       NUMERIC(8),
                PROT365     NUMERIC(8),
                PIC         NUMERIC(4),
                PERSISTANCE NUMERIC(4,1)
            );
        """)

        dst_cur.execute("DROP TABLE CL_LAITLACT;")
        dst_cur.execute("ALTER TABLE CL_LAITLACT_new RENAME TO CL_LAITLACT;")

        # ============================================================
        # CL_LAITCTRL (6 DATETIME + 2 FK)
        # ============================================================

        dst_cur.execute("""
            CREATE TABLE CL_LAITCTRL_new (
                ID_LAITCTRL       NUMERIC(9,0) PRIMARY KEY,
                ID_LAITEXPL       NUMERIC(7,0) NOT NULL
                                  REFERENCES CL_LAITEXPL(ID_LAITEXPL),
                ID_LAITLACT       NUMERIC(7) 
                                  REFERENCES CL_LAITLACT(ID_LAITLACT),

                HEURE_PREC2_DEB   DATETIME,
                HEURE_PREC2_FIN   DATETIME,
                HEURE_PREC_DEB    DATETIME,
                HEURE_PREC_FIN    DATETIME,
                HEURE_TRAIT1_DEB  DATETIME,
                HEURE_TRAIT1_FIN  DATETIME,

                LAIT_TRAIT1       NUMERIC(4,0),
                LAIT_TRAIT2       NUMERIC(4,0),
                LAIT_24_OBS       NUMERIC(4,0),
                POURC_PROT_24_OBS NUMERIC(5,2),
                POURC_MG_24_OBS   NUMERIC(5,2),
                CELL_24_OBS       NUMERIC(8,0),
                UREE_24_OBS       NUMERIC(4,0),
                LAIT_24_VAL       NUMERIC(4,0),
                POURC_PROT_24_VAL NUMERIC(5,2),
                POURC_MG_24_VAL   NUMERIC(5,2),
                CELL_24_VAL       NUMERIC(8,0),
                UREE_24_VAL       NUMERIC(4,0),
                LAIT_24_PREVU     NUMERIC(4,0)
            );
        """)

        dst_cur.execute("DROP TABLE CL_LAITCTRL;")
        dst_cur.execute("ALTER TABLE CL_LAITCTRL_new RENAME TO CL_LAITCTRL;")

        # ============================================================
        # Commit final
        # ============================================================

        dst_con.commit()
        dst_cur.execute("PRAGMA foreign_keys = ON;")
        print("Modifications applied with success")

    except Exception as e:
        
        dst_con.rollback()
        dst_cur.execute("PRAGMA foreign_keys = ON;")
        print(f"Error during data type consistency : {e}")
        raise #stop script

def Filling_CopyPasted_Tables(src_db,dst_db,df_AIDACTIEL_dst,df_CL_AIDE_ETAPE_CTRL_dst,df_CL_AIDE_TYPE_CTRL_dst):

    """
    This function takes the following parameters:
    - the connection to the source database
    - the connection to the destination database
    - a DataFrame containing data from the source database for the AIDACTIEL table
    - a DataFrame containing data from the source database for the CL_AIDE_ETAPE_CTRL table
    - a DataFrame containing data from the source database for the CL_AIDE_TYPE_CTRL table

    This function populates the destination database using the DataFrames provided as parameters.

    This function returns a boolean indicating whether the process completed successfully or not.
"""
    Go_on = True
    with sqlite3.connect(src_db, timeout=30) as src_conn, \
        sqlite3.connect(dst_db, timeout=30) as dst_conn:

        df_AIDACTIEL_dst.to_sql("AIDACTIEL", dst_conn, if_exists="append", index=False) 
        df_CL_AIDE_ETAPE_CTRL_dst.to_sql("CL_AIDE_ETAPE_CTRL", dst_conn, if_exists="append", index=False)
        df_CL_AIDE_TYPE_CTRL_dst.to_sql("CL_AIDE_TYPE_CTRL", dst_conn, if_exists="append", index=False)  
            
    return Go_on

def correct_ACTIEL_AIDACTIEL(df):
    """
Function that takes a DataFrame as input (ACTIEL_src DataFrame).

This function ensures that the ACTIEL field in the AIDACTIEL table has the correct data type and format:
- Sets ACTIEL as a VARCHAR in the database (if not already the case)
- Ensures values follow the expected format (e.g., 01, 02, 10, 11, XM, XL)

Returns:
- A corrected DataFrame ready to be inserted into the database
"""

    liste_actiel = df['ACTIEL'] #recovering data from actiel column of the df
    liste_actiel_ok=[]
    
    for actiel in liste_actiel: #browse each 'actiel'
        
        try: #try conversion int -> crash if actiel = XM XL,... (str)
            if len(str(actiel))==4 and str(actiel).find('.')!=-1: #10.0
                
                actiel_ok = str(int(actiel))
                
            elif len(str(actiel))==3 and str(actiel).find('.')!=-1: #8.0
                
                actiel_ok = "0"+str(int(actiel))
                
        
            else:#10
                actiel_ok = actiel
        except ValueError:#XM
            actiel_ok = actiel

        finally:
            liste_actiel_ok.append(actiel_ok)#prepare final list
    
    
    df['ACTIEL'] = liste_actiel_ok #correct input df
    return df

def correct_ACTIEL_IDENTANV(df):
    """
Function that takes a DataFrame as input (IDENTANV_src DataFrame).

This function ensures that the relevant field(s) in the IDENTANV table have the correct data types and formats.

Returns:
- pd.DataFrame: cleaned DataFrame ready for database insertion
"""

    liste_actiel = df['ACTIEL'] #recovering data from actiel column of the df
    liste_actiel_ok=[]
    
    
    for actiel in liste_actiel: #browse each 'actiel'
        
        try: #try conversion int -> crash if actiel = XM XL,... (str)
            if len(str(actiel))==4 and str(actiel).find('.')!=-1: #10.0
                
                actiel_ok = str(int(actiel))
                
            elif len(str(actiel))==3 and str(actiel).find('.')!=-1: #8.0
                
                actiel_ok = "0"+str(int(actiel))
                
            elif len(str(actiel))==1: #1
                actiel_ok = "0"+str(int(actiel))
            elif len(str(actiel))==2: #10 ou  #XM
                actiel_ok = actiel
            else:#10
                actiel_ok = actiel
        except ValueError:#XM
            actiel_ok = actiel

        finally:
            
            liste_actiel_ok.append(actiel_ok)#prepare final list
            
    
    df['ACTIEL'] = liste_actiel_ok #correct input df
    
    return df

def generate_index(nb,start,incr):
    '''
    Generates a usable list as an index
    # starting at the value given as 'start' input
    # generating a list of 'nb' (input) elements
    # with an increment of 'incr' (input) between each element
    '''
    liste = []
    liste.append(np.arange(start,start+nb,incr))
    return liste

def Generate_liste_proportions(df_src, Col_name, N_rows):
    '''

    This function takes as parameters:
    -   a DataFrame
    -   the name of the field in that DataFrame to analyze
    -   the number of rows to generate

    This function generates a list respecting the value proportions of the source database.
    This list will be of length [n_rows]

    This function returns a list that can be used in a DataFrame
    '''
    
    series = df_src[Col_name] #  taking only pd.series to be analyze
    distribution = series.value_counts(normalize=True)     # Calculation values repartition is a DF with values and proportions
    values = distribution.index.values  # Distinct values array
    probs = distribution.values #probabilities array
    
    # Generating new datas respecting input proportion
    Generated_datas = np.random.choice(    
        values,
        size=N_rows,
        p=probs
    )
    # Créating new DF
    new_df = pd.DataFrame({    
       
        "Gen_datas": Generated_datas
    })

    return new_df["Gen_datas"].to_list()   # Returning values list matching proportion et elem count

def Filling_exploitation():
    '''
    Function to fill the EXPLOITATION table in the database.
    Returns:
        - The list of postal codes (CP : XX00)
        - The list of table indexes (continuous)
        - A boolean indicating whether everything went smoothly
        - The number of farms generated
    '''

    global nb_fermes    # Global var to stock result
    nb_fermes = None    #Init variable
    go_on_exploitation = False #boolean statut
    liste_generated_CP=[]
    liste_EXPLOITATION_NOTINTEXPL=[]
    
    def valider():
        #Assure number farm to be generated is between 1 et 2000
        global nb_fermes
        try:
            nb_fermes = int(entry.get()) #Ask User
            if 1 <= nb_fermes <= 2000:
                
                root.destroy()  # Close if ok
            else:
                messagebox.showerror("Error", "Please enter a number between 1 et 2000")
        except ValueError:
                messagebox.showerror("Error", "Please enter a valid number not a string")
    
    # Interface creation
    root = tk.Tk()
    root.title("Farms generation")
    root.geometry("400x150")
    
    tk.Label(root, text="How many farms do you wish to generate (1-2000) ?", font=("Arial", 10)).pack(pady=15)
    
    entry = tk.Entry(root, font=("Arial", 12), width=10, justify='center')
    entry.pack(pady=5)
    entry.insert(0, "600")  # Default value
    entry.focus()  # Focus
    
    # Validate with enter key
    entry.bind('<Return>', lambda e: valider())

    #Define Button
    tk.Button(root, text="Valider", command=valider, bg="green", fg="white", font=("Arial", 11), padx=20, pady=5).pack(pady=15)
    
    root.mainloop()  # Waiting user validation
    
    # nb_fermes contains the value
    
    if ((nb_fermes is not None) and (nb_fermes!=0)) :
        df_filter_alive = dfs["EXPLOITATION"][dfs["EXPLOITATION"]["CODPOST"] != 0]#Removing farms with CODPOST = 0 in 
        def extract_municipality(row):
            return int((np.floor(row['CODPOST']/100))*100)

        df_filter_alive['Municipality'] = df_filter_alive.apply(extract_municipality,axis=1)
        df_filter_alive
        print(f"Generating {nb_fermes} farms...")
        liste_generated_CP = Generate_liste_proportions(df_filter_alive, "Municipality", nb_fermes) #generation farm number matching Municipality repartition
        liste_EXPLOITATION_NOTINTEXPL = generate_index(nb_fermes, 200000, 1)#genere l'index
        
        go_on_exploitation = True#all good, go on
    else:
        print("Opération annulée")

    #retourne les listes des champs de la table exploitation remplies, un boolean pour dire que tout ok et le nb_fermes rentrées par utilisateur

    return liste_generated_CP,liste_EXPLOITATION_NOTINTEXPL,go_on_exploitation,nb_fermes 

def Generate_IDENTANV(src_conn,dst_conn):

    '''
    Function to generate the IDENTANV table data.
    Takes as input the source and destination database cursors.
    Returns a boolean indicating whether everything went smoothly.
    Returns the dataframe ident_dst ready to be inserted into the database.
    '''
    go_on_identanv = False

    # Load used tables
    ident_src     = pd.read_sql("SELECT * FROM IDENTANV", src_conn)        # source
    explo_src     = pd.read_sql("SELECT * FROM EXPLOITATION", src_conn)    # source 
    explo_dst     = pd.read_sql("SELECT * FROM EXPLOITATION", dst_conn)    # destination 
    aidactiel_dst = pd.read_sql("SELECT * FROM AIDACTIEL", dst_conn)       # destination
    
    # Filter CODPOST = 0
    explo_dst = explo_dst[explo_dst["CODPOST"] != 0].copy()

    # DataType Consistency
    ident_src["ACTIEL"] = ident_src["ACTIEL"].astype(str)
    aidactiel_dst["ACTIEL"] = aidactiel_dst["ACTIEL"].astype(str)
 
 
    # 1) Jointure source + construction des troupeaux par CP/ferme (vaches vivantes)
 
    # Jointure source : vache + ferme + code postal
    ident_src_full = ident_src.merge(
    explo_src[["NOINTEXPL", "CODPOST"]],
    left_on="NOINTSANIT",
    right_on="NOINTEXPL",
    how="inner"
    )

    # On garde uniquement les vaches vivantes : NOINTSANIT != 111111 ou CODPOST != 0
    ident_vivantes_full = ident_src_full[ident_src_full["NOINTSANIT"] != 111111]
    ident_src_full = ident_src_full[ident_src_full["CODPOST"] != 0].copy()

    

    def extract_municipality(row):
       
        return int((np.floor(row['CODPOST']/100))*100)

    ident_src_full['Municipality'] = ident_src_full.apply(extract_municipality,axis=1)
    display(ident_src_full.shape)

    # Clean both columns before groupby
    ident_src_full['Municipality'] = ident_src_full['Municipality'].astype(str).str.strip()
    ident_src_full['NOINTSANIT']   = ident_src_full['NOINTSANIT'].astype(str).str.strip()


    ############################### Client wanted us to respect Number of breed per farms and number of cows in herd#########################################
    
     # Group (Municipality, NOINTSANIT) -> we got each value of municipality and farm number -> usefull to browse the result of the group by with the loop just after
    groupes_fermes = ident_src_full.groupby(["Municipality", "NOINTSANIT"])
    '''
    	      NOAN	SEXEAN	DTNAISANINV	NOINTSANIT	ACTIEL	NOANPERE	NOANMERE	NOINTEXPL	CODPOST	Municipality
    199	    15476617	F	20121104	503009	      01	13778903.0	13624379.0	503009	    7050	7000
    318	    15798786	F	20131218	502179	      02	14713824.0	15049136.0	502179	    6181	6100
    435	    16050004	F	20140920	511939	      04	15651422.0	15114705.0	511939	    7134	7100
    442	    16057774	F	20140929	510158	      04	NaN	        15450495.0	510158	    7830	7800
    460	    16082212	F	20141017	615761	      04	15502343.0	15423615.0	615761	    4730	4700
    ...	...	...	...	...	...	...	...	...	...	...
    99463	19564051	F	20210709	605842	      XM	NaN	        19557242.0	605842	    4770	4700
    99464	19564053	F	20210801	605842	      XM	NaN	        19564052.0	605842	    4770	4700
    99467	19584005	F	20201216	616690	      04	NaN	        19584004.0	616690	    4790	4700
    99468	19639291	F	20221016	605842	      XL	NaN	        19639290.0	605842	    4770	4700
    99469	19753145	F	20230812	616668	      XL	NaN	        19753144.0	616668	    4560	4500
    '''
    global s
    s = groupes_fermes
    #One DF per farm
    herds_by_cp = {} #herds_by_cp : {'75001': [df1, df2], '75002': [df3], ...}"
    all_herds = [] #([df1,df2,df...])
    
    for (muni, noint), df_ferme in groupes_fermes:#Browse group by result (muni,nointSANIT) and calling the filter result : df_ferme (number of cows for this farm)
        
        #if muni doesn't exist in dictionnary -> create with empty array
        #else return la associted array to this muni 
        #herds_by_cp : {'75001': [df1, df2], '75002': [df3], ...}"
        herds_by_cp.setdefault(muni, []).append(df_ferme)
        '''
        print(herds_by_cp)
        {'1300': [           
		NOAN 		SEXEAN  DTNAISANINV NOINTSANIT ACTIEL    NOANPERE    NOANMERE   NOINTEXPL  CODPOST Municipality 
9729   18072079      F     20201108     200448     04  		16422717.0  16017946.0   200448     1325         1300
12234  18762986      F     20221204     200448     04  		16851768.0  17864360.0   200448     1325         1300
18343  17417035      F     20181027     200448     02  		16990535.0  16044945.0   200448     1325         1300
20883  17813280      F     20200114     200448     02  		14609957.0  16894239.0   200448     1325         1300
22102  18404666      F     20211027     200448     04  		17804965.0  17162002.0   200448     1325         1300
23006  18153554      F     20210201     200448     04  		16854865.0  16295186.0   200448     1325         1300,
 
		NOAN 		SEXEAN  DTNAISANINV NOINTSANIT ACTIEL    NOANPERE    NOANMERE   NOINTEXPL  CODPOST Municipality 
6067   17122757      F     20171130     201309     04  		16626158.0  15959221.0   201309     1360         1300
7362   17867367      F     20200306     201309     04  		16821999.0  16767772.0   201309     1360         1300
21915  18312975      F     20210630     201309     40  		16668665.0  17444327.0   201309     1360         1300 ]}
        '''
        all_herds.append(df_ferme)#add the dataframe in the array
    '''
    print(all_herds)
    
    [NOAN       SEXEAN  DTNAISANINV NOINTSANIT ACTIEL     NOANPERE    NOANMERE   NOINTEXPL  CODPOST Municipality
    17605333      F     20190506     511938     02      16755746.0  16690281.0   511938     7812         7800     
    17812125      F     20200113     511938     02      16755746.0  15976471.0   511938     7812         7800  
    17978025      F     20200701     511938     02      16755746.0  16115164.0   511938     7812         7800  
    17980124      F     20200707     511938     02      16755746.0  16432997.0   511938     7812         7800 
    18698749      F     20220920     511938     02      17725169.0  17162259.0   511938     7812         7800,
    NOAN       SEXEAN  DTNAISANINV NOINTSANIT ACTIEL     NOANPERE    NOANMERE   NOINTEXPL  CODPOST Municipality
    18072079      F     20201108     200448     04      16422717.0  16017946.0    200448     1325        1300      
    18762986      F     20221204     200448     04      16851768.0  17864360.0   200448     1325         1300  
    17417035      F     20181027     200448     02      16990535.0  16044945.0   200448     1325         1300]
    
    '''
    
    # data type consistency ACTIEL like AIDACTIEL
    def format_actiel(value):
        s = str(value).strip()

        # ex : "5.0" -> "5")
        if s.endswith(".0"):
            s = s[:-2]

        # if only number -> format "01", "02", ..., "10"
        if s.isdigit():
            s = s.zfill(2)   # "1" -> "01", "9" -> "09", "10" -> "10"

        # else no action
        return s
    

    # Init Arrays
    muni_list = []         # array municipality for each generated cows
    nointsanit_list = [] # NOINTSANIT destination farms for each cows
    dtnais_list = []     # bithdte for each cows
    actiel_list = []     # breed for each cows

    def extract_municipality(row):
       
        return int((np.floor(row['CODPOST']/100))*100)

    explo_dst['Municipality'] = explo_dst.apply(extract_municipality,axis=1)

    # For each Municipality, a herd is assigned
    for cp_dest, fermes_dest_cp in explo_dst.groupby("Municipality"):#Browse

        '''
        print(cp_dest)
        print(fermes_dest_cp)
        1300
            NOINTEXPL  CODPOST  Municipality
        25      200025     1300          1300
        43      200043     1300          1300
        83      200083     1300          1300
        125     200125     1300          1300
        161     200161     1300          1300
        287     200287     1300          1300
        291     200291     1300          1300
        394     200394     1300          1300
        425     200425     1300          1300
        484     200484     1300          1300
        505     200505     1300          1300
        509     200509     1300          1300
        '''
        
        fermes_dest_cp = fermes_dest_cp.reset_index(drop=True)#reset index each time
        
        # Herds available for this CP if key CP in dictionnary-> use one df for this key  {'7500': [df1, df2]
        if cp_dest in herds_by_cp:
            herds_src = herds_by_cp[cp_dest]
        else:
            # if key doesn't exist -> use one df from all key
            herds_src = all_herds

        if not herds_src:
            continue  # safety continue

        nb_fermes_dest = len(fermes_dest_cp) # number of farm for this CP in destination 12 means there are 12 farms to fill
        
        troupeaux_assignes = []
        while len(troupeaux_assignes) < nb_fermes_dest:#while not each farm filled for this cp
            
            troupeaux_assignes.extend(herds_src)
            '''
            print(troupeaux_assignes)
            [           NOAN SEXEAN  DTNAISANINV NOINTSANIT ACTIEL    NOANPERE    NOANMERE  NOINTEXPL  CODPOST Municipality 
            9729   18072079      F     20201108     200448     04  16422717.0  16017946.0   200448     1325         1300
            12234  18762986      F     20221204     200448     04  16851768.0  17864360.0   200448     1325         1300
            18343  17417035      F     20181027     200448     02  16990535.0  16044945.0   200448     1325         1300
            ...,
                        NOAN SEXEAN  DTNAISANINV NOINTSANIT ACTIEL    NOANPERE    NOANMERE  NOINTEXPL  CODPOST Municipality 
            6067   17122757      F     20171130     201309     04  16626158.0  15959221.0   201309     1360         1300 
            7362   17867367      F     20200306     201309     04  16821999.0  16767772.0   201309     1360         1300 
            21915  18312975      F     20210630     201309     40  16668665.0  17444327.0   201309     1360         1300 
            ...,
            
            ...]
            '''
            
        troupeaux_assignes = troupeaux_assignes[:nb_fermes_dest] #assure nomber of herds to be generated
        
        random.shuffle(troupeaux_assignes) #shuffle to prevent bias

        # For each dest farm we copy the herds
        for i, (_, ferme_dest) in enumerate(fermes_dest_cp.iterrows()):#for each farm dest
            noint_dest = ferme_dest["NOINTEXPL"]
            troupeau_src = troupeaux_assignes[i]#recovering the matching herd

            for _, vache_src in troupeau_src.iterrows():#for each cows in this herd
                muni_list.append(cp_dest) #add cp
                nointsanit_list.append(noint_dest) #add NOINTSANIT
                dtnais_list.append(vache_src["DTNAISANINV"]) #add birthdate
                # ACTIEL formated like AIDACTIEL (01, 02, ..., CL, CV, ...)
                actiel_list.append(format_actiel(vache_src["ACTIEL"]))
    
    # Total number cows generated
    n_animaux = len(muni_list)
    print("Destination farms count :", explo_dst.shape[0])
    print("Generated cows count :", n_animaux)

    # NOAN : convention as is, could be changed
    NOAN_MIN = 13_665_449
    NOAN_MAX = 19_639_291
    noan_list = random.sample(range(NOAN_MIN, NOAN_MAX), n_animaux)

    # SEXEAN : all cows -> sexe = F
    sexean_list = ['F'] * n_animaux

    # 5) NOANPERE / NOANMERE (simple version)
#    - NOAMPERE = arbitrary (same format as NOAN)
#    - NOANMERE = random existing generated cows
    noanpere_list = []
    noanmere_list = []

    # Format as NOAN
    PERE_MIN = 99_000_000
    PERE_MAX = 99_999_999

    for _ in range(n_animaux): #for each cows
    
        # NOANPERE :
        pere = random.randint(PERE_MIN, PERE_MAX)
    
        # NOANMERE
        if random.random() < 0.8:   # 80% got a mother known (arbitrary)
            mere = random.choice(noan_list)
        else:
            mere = None
    
        noanpere_list.append(pere)
        noanmere_list.append(mere)
    # 6) DF construction

    ident_dst = pd.DataFrame({
        "NOAN": noan_list,
        "SEXEAN": sexean_list,
        "DTNAISANINV": dtnais_list,
        "NOINTSANIT": nointsanit_list,
        "ACTIEL": actiel_list,
        "NOANPERE": noanpere_list,
        "NOANMERE": noanmere_list,
    })
    ident_dst["NOANPERE"] = ident_dst["NOANPERE"].astype("Int64")   # entier nullable
    ident_dst["NOANMERE"] = ident_dst["NOANMERE"].astype("Int64")   # entier nullable
    
    go_on_identanv = True
    

    return go_on_identanv,ident_dst
    
def Generate_CLLAITEXPL(src_conn,dst_conn):
   
    """ 
    Function allowing to generate control type for each farms in EXPLOITATION table
    Args :
        Source/destination connector SQL
    Returns:
        go_on_CLLAITEXPLT, : Boolean everything ok 
        milkexpl_df['ID_LAITEXPL'].tolist(), : DF representing ID LAITEXPL
        milkexpl_df['NOINTEXPL'].tolist(),\ : DF representing NOINTEXPL(number of the farm) LAITEXPL
        milkexpl_df['DATE_CTRL'].tolist(), : DF representing DATE_CTRL LAITEXPL
        milkexpl_df['TRAIT1'].tolist(),\ : DF representing TRAIT1(AM or PM) LAITEXPL
        milkexpl_df['CD_TYPE_CTRL'].tolist(), : DF representing CD_TYPE_CTRL (type of control used for the farms -> each farm has only one type control) LAITEXPL
        milkexpl_df['DATE_RECEPT_ANALYSE'].tolist(),\ : DF representing DATE RECEPTION ANALYSE to the lab LAITEXPL
        milkexpl_df['CD_ETAPE_CTRL'].tolist() : DF representing control step LAITEXPL

   -"""
    
    df_expl_dst = pd.read_sql("SELECT * FROM EXPLOITATION", dst_conn) # destination EXPLOITATION
    df_CLLAITEXPL_src = pd.read_sql("Select * from CL_LAITEXPL", src_conn) # source CL_LAITEXPL
    go_on_CLLAITEXPLT = False

    fk_list = df_expl_dst['NOINTEXPL'].values  # array of farms number from exploitation destination
    nb_fk_list = len(fk_list)# Count farms exploitation destination

   #  Creating DF with UNIQUE farm number with a UNIQUE control type
    df_farmNb_unique = df_CLLAITEXPL_src[['NOINTEXPL', 'CD_TYPE_CTRL']].drop_duplicates(subset='NOINTEXPL') #subset : colomn to be considerate to drop duplicates

    df_farmNb_unique = df_farmNb_unique[df_farmNb_unique['CD_TYPE_CTRL'].notna()] #deleting farms without a defined control type
    df_farmNb_unique['CD_TYPE_CTRL'] = df_farmNb_unique['CD_TYPE_CTRL'].astype(int)# CD_TYPE_CTRL -as type int

   # Client request : control type = {1,2,9,10}
    allowed_vals = [1, 2, 9, 10]
    df_farmNb_unique = df_farmNb_unique[df_farmNb_unique['CD_TYPE_CTRL'].isin(allowed_vals)] #filter with criteria = client request

   # Generate new control type for new farm (destination)
    labels_CD_TYPE_CTRL = Generate_liste_proportions(
       df_farmNb_unique,  # DF with unique farm number
       'CD_TYPE_CTRL', #colomn to be considered
       nb_fk_list #Farm number exploitation destination
       )
    #Creating new DF farms/type contol info
    farms_Nb_CtrlType_info = pd.DataFrame({
       'NOINTEXPL': fk_list,
       'CD_TYPE_CTRL' : labels_CD_TYPE_CTRL
   })

    '''
    Count control for each farm depending on type controle for this farm:
    A4/AT4 (1,9) -> 4 weeks -> 28 jours;
    A6/AT6 (2,10) -> 6 weeks -> 42 jours.
    Considering 5 years -> Client request
    '''
    
    days_5y = 5 * 365 # 5 years
   
    n_4w = int(np.floor(days_5y / 28)) + 1   # find number of control considering 28 days between control
    n_6w = int(np.floor(days_5y / 42)) + 1   # find number of control considering 42 days between control
   
    rows = [] 
    for _, row in farms_Nb_CtrlType_info.iterrows():# Browse each farms
        Nointexpl = row['NOINTEXPL'] # Extract farm number
        label = str(row['CD_TYPE_CTRL']) # Extract TYPE_CTRL str

        if label in ['1', '9']:#if ctrl = 1 ou 9 (A4 ou AT4)
            n_rows = n_4w   # 4 weeks between ctrl
            interval_type = '4w'
        else:#else (A6 ou AT6)
            n_rows = n_6w   # 6 weeks between ctrl
            interval_type = '6w'

        for i in range(n_rows):
            # append in array dictionnary with farm name, type ctrl and interval
            rows.append({
                'NOINTEXPL': Nointexpl,
                'CD_TYPE_CTRL': label,
                'interval_type': interval_type # 4w 6w
            })

    #Creating DF with the right number of final rows -> will be returned
    milkexpl_df = pd.DataFrame(rows) 

    
    start_id = 700000
    milkexpl_df.insert(0, 'ID_LAITEXPL', np.arange(start_id, start_id + len(milkexpl_df))) #inserting into DF an ID
    
    #fill CD_ETAPE_CTRL with source proportion
    milkexpl_df['CD_ETAPE_CTRL'] = Generate_liste_proportions(
        df_CLLAITEXPL_src, ## CL_LAIT_EXPL - source
        'CD_ETAPE_CTRL',
        len(milkexpl_df)) #nb
    
    #------------------------------------------------------------------------------
    #Filling DATE_CTRL 

    years_first = 5 # 5 years ago first ctrl
    end_global   = pd.Timestamp.today().normalize()# TODAY
    start_global = end_global - pd.DateOffset(years=5) # Global periode (TODAY - 5 years)
    milkexpl_df['DATE_CTRL'] = pd.NaT

   # Specific periode = global periode
    start_first = start_global 
    end_first = start_global + pd.DateOffset(years=years_first)
   
   #For each farm
    for fk, grp in milkexpl_df.groupby('NOINTEXPL'): #For each farm
        interval_type = grp['interval_type'].iloc[0]#recovering '4w' or '6w'
        step_days = 28 if interval_type == "4w" else 42
        n_rows = len(grp)
        ##############################################
        # Select one date in defined interval
        total_days_first = (end_first - start_first).days
        offset_days = np.random.randint(0, total_days_first + 1)#randoms timedelta
        first_date = start_first + pd.Timedelta(days=offset_days) #First control defined

        # Nb control possible for this farm
        remaining_days = (end_global - first_date).days#nb days between first control and today
        max_controls_here = remaining_days // step_days + 1  #count possible control
    
        #security
        n_rows_adjusted = min(n_rows, max_controls_here)

        # security
        if n_rows_adjusted <= 0:
            continue

        # generate dates with step_days (28 or 42 days)
        dates = [
            first_date + pd.Timedelta(days=i * step_days)
            for i in range(n_rows_adjusted)
        ]
        milkexpl_df.loc[grp.index[:n_rows_adjusted], "DATE_CTRL_dt"] = dates #fill DF with dates array
    milkexpl_df['DATE_CTRL'] = milkexpl_df['DATE_CTRL_dt'].dt.strftime('%Y-%m-%d') #format str

    #------------------------------------------------------------------------------
    #Calculate avg duration between analyse reception to the lab and control date
   
    df_CLLAITEXPL_src['DATE_CTRL_dt'] = pd.to_datetime(df_CLLAITEXPL_src['DATE_CTRL']) #format
    df_CLLAITEXPL_src['DATE_RECEPT_ANALYSE'] = pd.to_datetime(df_CLLAITEXPL_src['DATE_RECEPT_ANALYSE']) #format

    #Let's find the last control date in the last 12 months (client request)
    last_date = df_CLLAITEXPL_src['DATE_CTRL_dt'].max() #find last date
    one_year_before = last_date - pd.DateOffset(years=1) #define date 12 months ago
    
   # filter 12 lasts months
    df_last12 = df_CLLAITEXPL_src[(df_CLLAITEXPL_src['DATE_CTRL_dt'] >= one_year_before) & (df_CLLAITEXPL_src['DATE_CTRL_dt'] <= last_date)].copy()

   # calculate time delta
   
    df_last12['delta_days'] = (df_last12['DATE_RECEPT_ANALYSE'] - df_last12['DATE_CTRL_dt']).dt.days

   # Average
    avg_delta = df_last12['delta_days'].mean()
    avg_delta_days = int(round(avg_delta))

   #####################################################################################
   ###################################################################################

    #Trnsform the timedelta (days count) in timedelta  and calculate Date recpt

    milkexpl_df['DATE_RECEPT_ANALYSE_dt'] = milkexpl_df['DATE_CTRL_dt'] + pd.to_timedelta(avg_delta_days, unit='D')
    milkexpl_df['DATE_RECEPT_ANALYSE'] = milkexpl_df['DATE_RECEPT_ANALYSE_dt'].dt.strftime('%Y-%m-%d')
    #-------------------------------------------------------------------------------------------
    #  Type control A ∈ {1,2}  repartition AM/PM according to proportion source

    mask_12 = milkexpl_df['CD_TYPE_CTRL'].isin(['1', '2'])
    nmbre_12 = mask_12.sum()

    df_old_12 = df_CLLAITEXPL_src[df_CLLAITEXPL_src['CD_TYPE_CTRL'].isin([1, 2])]
    milkexpl_df.loc[mask_12, 'TRAIT1'] = Generate_liste_proportions(
        df_old_12,   
        'TRAIT1',      
        nmbre_12)   
         
   #  Type contol AT ∈ {9,10} → alternate AM / PM (filtre le DF)
    mask_910 = milkexpl_df['CD_TYPE_CTRL'].isin(['9', '10'])

    for fk, grp in milkexpl_df[mask_910].groupby('NOINTEXPL'):#for each farms with type control AT
        grp_sorted = grp.sort_values('DATE_CTRL_dt')
        idx = grp_sorted.index
        n = len(idx)

        # random start: AM ou PM
        first_val = np.random.choice(['AM', 'PM'])

        # sequence AM/PM/AM/PM...
        values = []
        current = first_val
        for _ in range(n):
            values.append(current)
            current = 'PM' if current == 'AM' else 'AM'

        # fill TRAIT1 for this lines
        milkexpl_df.loc[idx, 'TRAIT1'] = values

    milkexpl_df = milkexpl_df[milkexpl_df["DATE_CTRL_dt"].notna()].copy()
    #sort by farm number and control date
    milkexpl_df = milkexpl_df.sort_values(["NOINTEXPL", "DATE_CTRL_dt"]).reset_index(drop=True)
   # ID
    start_id = 700000
    milkexpl_df["ID_LAITEXPL"] = range(start_id, start_id + len(milkexpl_df))
      
    # Final DF
    milkexpl_df = milkexpl_df[['ID_LAITEXPL', 'NOINTEXPL', 'DATE_CTRL', 'TRAIT1', 'CD_TYPE_CTRL', 'DATE_RECEPT_ANALYSE', 'CD_ETAPE_CTRL']]
    go_on_CLLAITEXPLT = True
    return go_on_CLLAITEXPLT,milkexpl_df['ID_LAITEXPL'].tolist(),milkexpl_df['NOINTEXPL'].tolist(),\
        milkexpl_df['DATE_CTRL'].tolist(),milkexpl_df['TRAIT1'].tolist(),\
        milkexpl_df['CD_TYPE_CTRL'].tolist(),milkexpl_df['DATE_RECEPT_ANALYSE'].tolist(),\
        milkexpl_df['CD_ETAPE_CTRL'].tolist()

def recovery_nolact(src_cur):
    
    '''
    Function recovering Number of lactation per cow and occurence proportion for each CP /ACTIEL (breed)
    Creating a dataframe as:
    CODPOST ACTIEL NB_LACT proportion
    1301    04      1       0.42
    1301    04      2       0.58
    1325    01      1       0.5
    1325    01      2       0.5
    1325    04      1       0.33
    1325    04      2       0.33
    1325    04      3       0.33

    Args : input cursor

    return :
    DF

    '''
                        
    avg_per_actiel = src_cur.execute(
        """
                                
        SELECT 
            ex.CODPOST,
            ia.ACTIEL,
            ll.NOLACT AS Nb_LACT,
            CAST(COUNT(*) AS FLOAT) / SUM(COUNT(*)) OVER (PARTITION BY ex.CODPOST, ia.ACTIEL) AS repartition_nb_lact
        FROM 
            IDENTANV ia 
            JOIN CL_LAITLACT ll ON ll.NOAN = ia.NOAN 
            JOIN EXPLOITATION ex ON ia.NOINTSANIT = ex.NOINTEXPL 
        WHERE 
            ex.NOINTEXPL != 111111
        GROUP BY 
            ex.CODPOST, 
            ia.ACTIEL, 
            ll.NOLACT
        ORDER BY 
            ex.CODPOST, 
            ia.ACTIEL, 
            ll.NOLACT               
                                                                                                
        """)
                                                                                                        
    fetch = avg_per_actiel.fetchall()
                                                                                                       
    df = pd.DataFrame(fetch, columns=['CODPOST','ACTIEL', 'Nb_lact','Repartition'])
                                                                                                                        
    return df#return df with 4 columns

def sample_nb_lact(codpost, actiel, df_dist):

    """
    Function allowing to determinate the number of lactation for a cow taking into consideration input database proportion
    Args:
        Codpost to be considered (of the current cow)
        Actiel to be considered (of the current cow) returning 
        df_dist :
                            #CP     ACTIEL      nb_lactation     proportion 
                            #1001     04            2               0.4
                            #1001     04            3               0.2
                            #1001     04            4               0.4
                            #1001     02            3               0.35
                            #1001     02            4               0.35
                            #1001     02            5               0.3
                            #1002     10            6               0.35
                            #1002     10            7               0.35
                            #1002     10            8               0.3
    """
    # Filter DF with CP and Actiel
    mask = (df_dist['CODPOST'] == codpost) & (df_dist['ACTIEL'] == actiel)
    options = df_dist[mask]
    
    
    if len(options) == 0: # if no match -> filter on ACTIEL only
        mask = (df_dist['ACTIEL'] == actiel)
        options = df_dist[mask]
        if len(options) == 0: # if no match -> filter on CODPOST only
            mask = (df_dist['CODPOST'] == codpost)
            options = df_dist[mask]
            if len(options) ==0 : #if no match -> return 1
                return 1
        
    # returning Nb_lact with input dabase proportion taking into consideration
    return np.random.choice(
        options['Nb_lact'].values,
        p=options['Repartition'].values / options['Repartition'].sum()  # Normalized
    )

def nombre_total_lactation(df_IDENTANV_JOIN_EXPL_dst):
    '''
    Function alolowing to count the total number of lactation for all cows in IDENTANV dest
    Args :
    df_IDENTANV_JOIN_EXPL
    #Exemple :
                            #NOAN       SEXEAN      DTNAISANINV     NOINTSANIT      ACTIEL      NOANPERE     NOANMERE   NOINTEXPL   CODPOST     Nblact
                            #15994855      F            20210314       200139         04         99999493    99523596      200139     1001        4
                            #15994856      F            20210314       200139         04         99999493    99523596      200139     1001        2
    Return:
        Integer count
    '''
    
    Nb_LACT_total = sum(df_IDENTANV_JOIN_EXPL_dst['Nb_lact'])
    
    return Nb_LACT_total

def generate_NOAN_NOLACT_CLLAITLACT(df_IDENTANV_JOIN_EXPL_dst):
    '''
    Function allowing to generate liste used to fill NOAN and NOLACT in the CL_LAITLACT table
    args:
        df_IDENTANV_JOIN_EXPL
        #Exemple :
                            #NOAN       SEXEAN      DTNAISANINV     NOINTSANIT      ACTIEL      NOANPERE     NOANMERE   NOINTEXPL   CODPOST     Nblact
                            #15994855      F            20210314       200139         04         99999493    99523596      200139     1001        4
                            #15994856      F            20210314       200139         04         99999493    99523596      200139     1001        2
    How?
    Read Nblact and insert N times the values 'number of the cow' in NOAN array and incremental count in NOLACT (1,2,3,4,....)
    Return:
        NOAN array : [15994855,15994855,15994855,15994855,15994856,15994856,...]
        NOLACT array : [1,2,3,4,1,2,....]
    '''
    liste_NOAN = []
    liste_NO_LACT =[]
    for i in range(df_IDENTANV_JOIN_EXPL_dst.shape[0]): #for each cows
        Noan = df_IDENTANV_JOIN_EXPL_dst['NOAN'][i] #recovering cow number
        Nb_lact = df_IDENTANV_JOIN_EXPL_dst['Nb_lact'] # recovering nbLact column
        for j in range (int(Nb_lact[i])):#loop for NbLact times for the considered cow
            liste_NOAN.append(Noan)
            liste_NO_LACT.append(j+1)
    
    return liste_NOAN,liste_NO_LACT

def generate_index(nb,start,incr):
    '''
    Function allowing to generate an array by defining a start value, a step and a number of elem in inputs
    '''
    liste = []
    liste.append(np.arange(start,start+nb,incr))
    return liste

def avg_duree_lactation_per_ACTIEL_per_CP_per_NO_LACT(src_cur):
    '''
    Function allowing to create a df regrouping each CP,ACTIEL and NoLACT + the vlue of avg lactation time + proportion
     #return DF  for each CP, ACTIEL and NOLACT the lactation time and the proportion of occurence
                            #EXEMPLE
                            #CP     ACTIEL      NOLACT      avg(DATE_TAR - DATE_VEL) en mois     proportion
                            #1001       04          1                   10                          0.1
                            #1001       04          1                   11                          0.5
                            #1001       04          1                   12                          0.4
                            #1001       04          2                   10                          0.2
                            #1001       04          2                   11                          0.2
                            #1001       04          2                   12                          0.6
                            #       ....
    Args:
        cursor towards input DB
    return:
        df
    '''
    
    avg_dur_lact = src_cur.execute("""
    
    WITH calcul_diff AS (
    SELECT 
        CAST(ai.ACTIEL AS TEXT) AS ACTIEL,
        ex.CODPOST,
        cl.NOLACT AS No_LACT,
        ia.DTNAISANINV,
        DATE(SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 1, 4) || '-' || 
             SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 5, 2) || '-' || 
             SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 7, 2)) AS date_naissance,
        cl.DATE_VEL,
        cl.DATE_TAR,
        CASE 
            WHEN cl.NOLACT = 1 THEN 
                CAST((JULIANDAY(cl.DATE_VEL) - JULIANDAY(DATE(SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 1, 4) || '-' || 
                                                          SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 5, 2) || '-' || 
                                                          SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 7, 2))))/30.44 AS INTEGER)
            ELSE 
                CAST((JULIANDAY(cl.DATE_VEL) - JULIANDAY(cl_prev.DATE_VEL))/30.44 AS INTEGER)
        END AS diffe_2_lact_calc
    FROM CL_LAITLACT cl
    JOIN IDENTANV ia ON cl.NOAN = ia.NOAN
    JOIN AIDACTIEL ai ON ai.ACTIEL = ia.ACTIEL
    JOIN EXPLOITATION ex ON ia.NOINTSANIT = ex.NOINTEXPL
    LEFT JOIN CL_LAITLACT cl_prev ON cl.NOAN = cl_prev.NOAN 
                                   AND cl_prev.NOLACT = cl.NOLACT - 1
    WHERE cl.DATE_TAR IS NOT NULL 
      AND cl.DATE_VEL IS NOT NULL 
      AND ia.NOINTSANIT != 111111
)
SELECT 
    ACTIEL,
    CODPOST,
    No_LACT,
    DTNAISANINV,
    date_naissance,
    DATE_VEL,
    DATE_TAR,
    COALESCE(
        diffe_2_lact_calc,
        CAST(AVG(diffe_2_lact_calc) OVER (PARTITION BY ACTIEL, CODPOST, No_LACT) AS INTEGER),
        10
    ) AS diffe_2_lact,
    ROUND(
        COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY ACTIEL, CODPOST, No_LACT), 
        2
    ) AS prop_dur_2_lact
FROM calcul_diff
GROUP BY ACTIEL, CODPOST, No_LACT, diffe_2_lact_calc
ORDER BY ACTIEL, CODPOST, No_LACT, diffe_2_lact;
    """)
    # ACTIEL CODPOST NOLACT DTNAIS      Birthdate    DATE Vel   Date TAR    Count_Months_between_2VEL             Proportion
#     01	  1495	   1	20210210	2021-02-10	2023-05-12	2024-10-10	            26	                         0.14
    # 01	  1495	   1	20210220	2021-02-20	2023-10-02	2024-07-26	            31	                         0.14
    # 01	  1495	   1	20210728	2021-07-28	2024-07-07	2024-11-21	            35	                         0.14
    # 01	  1495	   1	20190205	2019-02-05	2022-03-23	2022-08-03	            37	                         0.14
    # 01	  1495	   1	20180205	2018-02-05	2021-08-31	2022-06-20	            42	                         0.14
    # 01	  1495	   1	20190310	2019-03-10	2022-12-26	2023-05-18	            45	                         0.14
    # 01	  1495	   1	20190218	2019-02-18	2023-03-19	2023-10-31	            48	                         0.14
    # 01	  1495	   2	20190218	2019-02-18	2024-03-09	2025-01-03	            11	                         0.2

    
    fetch = avg_dur_lact.fetchall()
    
    #genate DF
    df = pd.DataFrame(fetch, columns=['ACTIEL','CODPOST','NOLACT','DNaissance','Date_Naissance','DATE_VEL','DATE_TAR','Diff_2_lact','prop_dur_2_lact'])
    
    return df

def Fill_Date_Vel_Par_IDLACT(df_avg,df_tmp=None):
    '''
    Function allowing to fill DATE_VEL generated in output DF based on infos already output DB
    ARgs:
        df_avg :
    #CP     ACTIEL      NOLACT      Count_Months_between_2VEL            proportion
    #1001       04          1                   10                          0.1
    #1001       04          1                   11                          0.5
    #1001       04          1                   12                          0.4
    #1001       04          2                   10                          0.2
    #1001       04          2                   11                          0.2
    #1001       04          2                   12                          0.6

    return a tmp_df with filled DATE_VEL


    '''
    
    # ============
    # 1) Extraction SQL 
    # ============
    fetch = dst_cur.execute("""
        select cl.ID_LAITLACT,cl.NOAN,cl.NOLACT, ia.ACTIEL,cl.DATE_VEL,cl.DATE_TAR,ex.CODPOST,
        DATE(SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 1, 4) || '-' || 
             SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 5, 2) || '-' || 
             SUBSTR(CAST(ia.DTNAISANINV AS TEXT), 7, 2)) AS date_naissance
        
        from CL_LAITLACT cl
        LEFT JOIN IDENTANV ia ON cl.NOAN = ia.NOAN
        LEFT JOIN EXPLOITATION ex on ia.NOINTSANIT = ex.NOINTEXPL
		ORDER by cl.NOAN,cl.NOLACT,ex.CODPOST,ia.ACTIEL;
        
    """).fetchall()
    '''
    fetch :
    ID_LAITLACT NOAN      NOLACT  ACTIEL DATE VEL   Date_TAR    CODPOST birthdate
    3506312	    12992314	1	    02	2018-11-03	2020-01-13	   0	2016-09-28
    3603213	    12992314	2	    02	2020-03-17	2021-06-03	   0	2016-09-28
    3705033	    12992314	3	    02	2021-07-18	2022-05-31	   0	2016-09-28
    3814246	    12992314	4	    02	2022-07-08		           0	2016-09-28
    3371284	    13232677	14	    02	2016-11-26	2019-05-10	   0	2000-09-08
    '''
    #CTmp DF creation (DATE_VEL and DATE_TAR are None at this moment)
    df_tmp = pd.DataFrame(fetch, columns=[
       'ID_LAITLACT','NOAN','NOLACT','ACTIEL','DATE_VEL','DATE_TAR','CODPOST','Date_naissance'
    ])

    df_tmp["Date_naissance"] = pd.to_datetime(df_tmp["Date_naissance"]) #cast as dt

    df_avg = df_avg.copy()

    # Probability normalisation
    df_avg["prop_norm"] = df_avg.groupby(
        ["ACTIEL", "CODPOST", "NOLACT"]
    )["prop_dur_2_lact"].transform(lambda x: x / x.sum())

    '''
    print(df_avg.head(10))
  ACTIEL  CODPOST  NOLACT  DNaissance Date_Naissance    DATE_VEL    DATE_TAR  Diff_2_lact  prop_dur_2_lact  prop_norm
0     01     1495       1    20210210     2021-02-10  2023-05-12  2024-10-10           26             0.14   0.142857
1     01     1495       1    20210220     2021-02-20  2023-10-02  2024-07-26           31             0.14   0.142857
2     01     1495       1    20210728     2021-07-28  2024-07-07  2024-11-21           35             0.14   0.142857
3     01     1495       1    20190205     2019-02-05  2022-03-23  2022-08-03           37             0.14   0.142857
4     01     1495       1    20180205     2018-02-05  2021-08-31  2022-06-20           42             0.14   0.142857
5     01     1495       1    20190310     2019-03-10  2022-12-26  2023-05-18           45             0.14   0.142857
6     01     1495       1    20190218     2019-02-18  2023-03-19  2023-10-31           48             0.14   0.142857
7     01     1495       2    20190218     2019-02-18  2024-03-09  2025-01-03           11             0.20   0.200000

    '''
    

    lookup_dict = {}
    
    for (actiel, codpost, nolact), group in df_avg.groupby(["ACTIEL", "CODPOST", "NOLACT"]): # for each rows in the groupby 
        #creating a key in the dict with valus : dict (durées : [],probs: [])
        lookup_dict[(actiel, codpost, nolact)] = {
            'durees': group["Diff_2_lact"].values,
            'probs': group["prop_norm"].values
        }
        
        '''
        print(lookup_dict)
        {
        ('01', np.int64(1495), np.int64(1)): 
            {'durees': array([26, 31, 35, 37, 42, 45, 48]), 
            'probs': array([0.14285714, 0.14285714, 0.14285714, 0.14285714, 0.14285714,0.14285714, 0.14285714])}
        ,
        {...
        }}
        '''

    
    # Fallback for CP+ ACTIEL only
    lookup_actiel_cp = {}
    for (actiel, nolact), group in df_avg.groupby(["ACTIEL", "CODPOST"]):
        lookup_actiel_cp[(actiel, nolact)] = {
            'durees': group["Diff_2_lact"].values,
            'probs': group["prop_norm"].fillna(0).values
        }
        # Normalize
        total = lookup_actiel_cp[(actiel, nolact)]['probs'].sum()
        if total > 0:
            lookup_actiel_cp[(actiel, nolact)]['probs'] /= total
    
    # Fallback for ACTIEL only
    lookup_actiel = {}
    for actiel, group in df_avg.groupby("ACTIEL"):
        lookup_actiel[actiel] = {
            'durees': group["Diff_2_lact"].values,
            'probs': group["prop_norm"].fillna(0).values
        }
        total = lookup_actiel[actiel]['probs'].sum()
        if total > 0:
            lookup_actiel[actiel]['probs'] /= total

    # ============================
    #  Determine time between 2 VEL for this cow
    # ============================
    def tirage_vectorise_par_groupe(group_df):
        """Function allowing to determine time between 2 VEL with a proportion notion
        args:
            groupby DF by ACTIEL,CODPOST and NOLACT
        return:
        # if durees = [10, 20, 30] et len(group_df) = 5
        #array([20, 10, 30, 10, 20])
            """
        if len(group_df) == 0:
            return []
        # F
        row = group_df.iloc[0]
        a, cp, nl = row["ACTIEL"], row["CODPOST"], row["NOLACT"]
        
        # Hiérarchie de fallback
        if (a, cp, nl) in lookup_dict: #sur actiel,codpost et nolact
            data = lookup_dict[(a, cp, nl)]
        elif (a, cp) in lookup_actiel_cp:#sur actiel,codpost
            data = lookup_actiel_cp[(a, cp)]
        elif a in lookup_actiel: #sur actiel seul
            data = lookup_actiel[a]
        else:
            # Fallback par défaut
            data = {'durees': np.array([10]), 'probs': np.array([1.0])}
        
        durees = data['durees']
        probs = data['probs']
        
        # Normalisation de sécurité
        if probs.sum() == 0:
            probs = np.ones(len(probs)) / len(probs)
        else:
            probs = probs / probs.sum()
        
        # return:
        # if durees = [10, 20, 30] et len(group_df) = 5
        #array([20, 10, 30, 10, 20])
        return np.random.choice(durees, size=len(group_df), p=probs)

    # Apply function by group 
    df_tmp["duree_finale"] = df_tmp.groupby(["ACTIEL", "CODPOST", "NOLACT"], group_keys=False).apply(
        lambda g: pd.Series(tirage_vectorise_par_groupe(g), index=g.index)
    )
    '''
    print("df_tmp_bef_cumsum",df_tmp)
                  ID_LAITLACT      NOAN     NOLACT ACTIEL DATE_VEL DATE_TAR  CODPOST Date_naissance  duree_finale
    0               3531061     13683956       1     04     None     None     4700     2022-09-19            25
    1               3531338     13688683       1     CM     None     None     4900     2019-02-10            23
    2               3531331     13720330       1     40     None     None     4900     2021-03-09            13
    3               3531414     13747621       1     02     None     None     5000     2021-12-05            12
    4               3531067     13764917       1     04     None     None     4700     2022-03-20            27
    ..           ...       ...     ...    ...      ...      ...      ...            ...           ...
    583             3531070     19591507       1     04     None     None     4700     2021-12-16            27
    584             3531071     19591507       2     04     None     None     4700     2021-12-16            12
    585             3531072     19591507       3     04     None     None     4700     2021-12-16            12
    586             3531073     19591507       4     04     None     None     4700     2021-12-16            12
    587             3531074     19591507       5     04     None     None     4700     2021-12-16            12
    '''
    # cumsum for each cow
    df_tmp = df_tmp.sort_values(["NOAN", "NOLACT"])
    df_tmp["duree_cumulee"] = df_tmp.groupby("NOAN")["duree_finale"].cumsum()
    '''
    print("df_tmp_aft_cumsum",df_tmp)
        ID_LAITLACT      NOAN       NOLACT ACTIEL DATE_VEL DATE_TAR  CODPOST Date_naissance  duree_finale  duree_cumulee
0        3531061       13683956       1     04     None     None     4700     2022-09-19            25             25
1        3531338       13688683       1     CM     None     None     4900     2019-02-10            23             23
2        3531331       13720330       1     40     None     None     4900     2021-03-09            13             13
3        3531414       13747621       1     02     None     None     5000     2021-12-05            12             12
4        3531067       13764917       1     04     None     None     4700     2022-03-20            27             27
..           ...       ...     ...    ...      ...      ...      ...            ...           ...            ...
583      3531070       19591507       1     04     None     None     4700     2021-12-16            27             27
584      3531071       19591507       2     04     None     None     4700     2021-12-16            12             39
585      3531072       19591507       3     04     None     None     4700     2021-12-16            12             51
586      3531073       19591507       4     04     None     None     4700     2021-12-16            12             63
587      3531074       19591507       5     04     None     None     4700     2021-12-16            12             75

    '''

    # Calculate DATE VEL from Birth Date
    df_tmp["DATE_VEL"] = df_tmp["Date_naissance"] + pd.to_timedelta(df_tmp["duree_cumulee"] * 30, unit="D")
    '''
    print("df_tmp_final",df_tmp)
        ID_LAITLACT      NOAN       NOLACT ACTIEL   DATE_VEL DATE_TAR  CODPOST Date_naissance  duree_finale  duree_cumulee
0        3531061        13683956       1     04 2024-10-08     None     4700     2022-09-19            25             25
1        3531338        13688683       1     CM 2020-12-31     None     4900     2019-02-10            23             23
2        3531331        13720330       1     40 2022-04-03     None     4900     2021-03-09            13             13
3        3531414        13747621       1     02 2022-11-30     None     5000     2021-12-05            12             12
4        3531067        13764917       1     04 2024-06-07     None     4700     2022-03-20            27             27
..           ...       ...     ...    ...        ...      ...      ...            ...           ...            ...
583      3531070        19591507       1     04 2024-03-05     None     4700     2021-12-16            27             27
584      3531071        19591507       2     04 2025-02-28     None     4700     2021-12-16            12             39
585      3531072        19591507       3     04 2026-02-23     None     4700     2021-12-16            12             51
586      3531073        19591507       4     04 2027-02-18     None     4700     2021-12-16            12             63
587      3531074        19591507       5     04 2028-02-13     None     4700     2021-12-16            12             75
    '''
    return df_tmp #retourne le DF avec DATE_VEL remplie

def avg_duree_VEL_TAR_per_ACTIEL_per_CP_per_NO_LACT(src_cur):
    '''
    Function allowing to calculate the AVG duration between DATE VEL and DATE TAR by ACTIEL/CP/NOLACT
    args :
        input cursor toward input DB
    Return:
        DF as :
    ID_LAITLACT     ACTIEL  CODPOST NOLACT  DATE_VEL    DATE_TAR    diff VEL_TAR(months)    Proportion
    3949836	          01	1400	1	    2024-07-07	2024-11-21	4	                    0.43
    3866075	          01	1400	1	    2023-03-19	2023-10-31	7	                    0.14
    3777903	          01	1400	1	    2021-08-31	2022-06-20	9	                    0.29
    3872479	          01	1400	1	    2023-05-12	2024-10-10	16	                    0.14
    3872480	          01	1400	2	    2023-04-25	2023-10-31	6	                    0.2
    3786666           01    1500    1                               1                       0.5
    3786666           01    1500    1                               2                       0.5
    ...
    
    '''
    
    
    avg_dur_lact = src_cur.execute("""
    WITH calcul_diff AS (
    SELECT 
        cl.ID_LAITLACT,
        CAST(ai.ACTIEL AS TEXT) AS ACTIEL,
        floor(ex.CODPOST/100)*100 as CODPOST,
        cl.NOLACT AS No_LACT,
        cl.DATE_VEL,
        cl.DATE_TAR,
		CAST((JULIANDAY(cl.DATE_TAR) - (JULIANDAY(cl.DATE_VEL)))/30.44 AS INTEGER) AS Diff_TAR_VEL
    FROM CL_LAITLACT cl
    JOIN IDENTANV ia ON cl.NOAN = ia.NOAN
    JOIN AIDACTIEL ai ON ai.ACTIEL = ia.ACTIEL
    JOIN EXPLOITATION ex ON ia.NOINTSANIT = ex.NOINTEXPL
    WHERE cl.DATE_TAR IS NOT NULL 
      AND cl.DATE_VEL IS NOT NULL 
      AND ia.NOINTSANIT != 111111
    )
    SELECT 
        ID_LAITLACT,
        ACTIEL,
        CODPOST,
        No_LACT,
        DATE_VEL,
        DATE_TAR,
        COALESCE(
            Diff_TAR_VEL,
            CAST(AVG(Diff_TAR_VEL) OVER (PARTITION BY ACTIEL, CODPOST, No_LACT) AS INTEGER)
        ) AS diff_TAR_VEL,
        ROUND(
            COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY ACTIEL, CODPOST, No_LACT), 
            2
        ) AS prop_dur_TAR_VEL
    FROM calcul_diff
    GROUP BY ACTIEL, CODPOST, No_LACT, Diff_TAR_VEL
    ORDER BY ACTIEL, CODPOST, No_LACT, Diff_TAR_VEL;   
   
    """)
    
    fetch = avg_dur_lact.fetchall()
    
    #genere un dataframe avec les données
    df = pd.DataFrame(fetch, columns=['ID_LAITLACT','ACTIEL','CODPOST','NOLACT','DATE_VEL','DATE_TAR','Diff_TAR_VEL','prop_dur_TAR_VEL'])
    
    return df

def Generate_DATE_TAR(df_avg, df_tmp):
    """
    Function allowing to determine DATE_TAR. It will :
        pick a duration between DATE_VEL and DATE_TAR considering ACTIEL/CODPOST/NOLACT and proportion of occurence
    Args:

      - df_avg : DF with avg and proportion duration between VEL and TAR by ACTIEL / CODPOST / NOLACT
      - df_tmp : DF containing cows from output DB with DATE VEL generated
    Return :
      - array with DATE_TAR generated
      - df_tmp (modified with DATE_TAR generated included)
    """
    
    df_avg = df_avg.copy()
    
    # Normalisation
    df_avg["prop_norm"] = df_avg.groupby(
        ["ACTIEL", "CODPOST", "NOLACT"]
    )["prop_dur_TAR_VEL"].transform(lambda x: x / x.sum())

    # Created dict
    lookup_dict = {}
    for (actiel, codpost, nolact), group in df_avg.groupby(["ACTIEL", "CODPOST", "NOLACT"]):
        lookup_dict[(actiel, codpost, nolact)] = {
            'durees': group["Diff_TAR_VEL"].values,
            'probs': group["prop_norm"].values
        }
        '''
        print(lookup_dict)
        {
        ('01', np.int64(1495), np.int64(1)): 
            {'durees': array([26, 31, 35, 37, 42, 45, 48]), 
            'probs': array([0.14285714, 0.14285714, 0.14285714, 0.14285714, 0.14285714,0.14285714, 0.14285714])}
        ,
        {...
        }}
        '''
    
    lookup_actiel_cp = {}
    for (actiel, nolact), group in df_avg.groupby(["ACTIEL", "CODPOST"]):
        lookup_actiel_cp[(actiel, nolact)] = {
            'durees': group["Diff_TAR_VEL"].values,
            'probs': group["prop_norm"].fillna(0).values
        }
        total = lookup_actiel_cp[(actiel, nolact)]['probs'].sum()
        if total > 0:
            lookup_actiel_cp[(actiel, nolact)]['probs'] /= total
    
    lookup_actiel = {}
    for actiel, group in df_avg.groupby("ACTIEL"):
        lookup_actiel[actiel] = {
            'durees': group["Diff_TAR_VEL"].values,
            'probs': group["prop_norm"].fillna(0).values
        }
        total = lookup_actiel[actiel]['probs'].sum()
        if total > 0:
            lookup_actiel[actiel]['probs'] /= total

    def tirage_vectorise_par_groupe(group_df):
        '''
        Function defining the duration between DATE VEL and DATE TAR
        args :
        groupby input DB by CTIEL/CODPOST/NOLACT
        return the value defined
        '''
        if len(group_df) == 0:
            return []
        
        row = group_df.iloc[0]
        a, cp, nl = row["ACTIEL"], row["CODPOST"], row["NOLACT"]
        
        if (a, cp, nl) in lookup_dict: #if match with ACTIEL, cp et NOLACT
            data = lookup_dict[(a, cp, nl)] #return values/proportions
        elif (a, nl) in lookup_actiel_cp:
            data = lookup_actiel_cp[(a, nl)]
        elif a in lookup_actiel:
            data = lookup_actiel[a]
        else:
            data = {'durees': np.array([10]), 'probs': np.array([1.0])}
        
        durees = data['durees']
        probs = data['probs']
        
        if probs.sum() == 0:
            probs = np.ones(len(probs)) / len(probs)
        else:
            probs = probs / probs.sum() #normalize
        
        # Defining
        tirages = np.random.choice(durees, size=len(group_df), p=probs)
        # 2 months minimum between DATE_TAR previous and DATE VEL actual (client requests)
        tirages = np.maximum(tirages, 2)
        return tirages

    df_tmp["duree_VELTAR"] = df_tmp.groupby(["ACTIEL", "CODPOST", "NOLACT"], group_keys=False).apply(
        lambda g: pd.Series(tirage_vectorise_par_groupe(g), index=g.index)
    )

    df_tmp = df_tmp.sort_values(["NOAN", "NOLACT"])
    df_tmp["duree_cumulee"] = df_tmp.groupby("NOAN")["duree_VELTAR"].cumsum()
    df_tmp["DATE_TAR"] = df_tmp["DATE_VEL"] + pd.to_timedelta(df_tmp["duree_cumulee"] * 30, unit="D")

    return df_tmp

if __name__ == "__main__":

   ##############################################################################################################
    #                                                                                                            
    #                                                   MAIN EXECUTE                                                                                                 
    #                                                 0 - Launch Script                                                               
    ##############################################################################################################
    
    print("0 - Launch script")                     
    ##############################################################################################################
    #                                                                                                            
    #                                              1 - Initialization Script                                                                                         #
    #                                                                                                                
    ############################################################################################################## 

    print("1 - Initialization Script")
    

    ##############################################################################################################

    current_dir = Path(__file__).resolve().parent
    input_db = current_dir / "db_cl_eleveo_v2.db"       #input path
    output_db = current_dir / "db_cl_eleveo_New.db" #output path
    print(f"Chemin de la source : {input_db}")

    # Separation between copypasted tables, generated tables and regressed tables

    Array_Tables_Name_CopyPasted,Array_Tables_Generated,Array_Tables_Regressed=["AIDACTIEL","CL_AIDE_ETAPE_CTRL","CL_AIDE_TYPE_CTRL"],\
                            ["EXPLOITATION","IDENTANV"],\
                            ["CL_LAITCTRL","CL_LAITEXPL","CL_LAITLACT"]

    ##############################################################################################################
    #                                                                                                            
    #                                         2 - Deleting output DB if exists                                                                                        #
    #                                                                                                                
    ############################################################################################################## 
    
    Go_on_Suppression = Deleting_output_DB(output_db)#Deleting output DB if exists

    ##############################################################################################################
    #                                                                                                            
    #                                         3 - Connecting Input DB                                                                                   #
    #                                                                                                                
    ############################################################################################################## 

    if Go_on_Suppression:
    # Connecting input
        print("3 - Connecting input DB")  
        
        src_conn = sqlite3.connect(input_db) #connecting input DB
        src_cur = src_conn.cursor() #cursor creation towards input DB
        tables = src_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall() #Recovering each tables names

        '''Creating a dictionnary with key = table_name and values = datas from this table'''
        dfs = {}
        for (table_name,) in tables:
            dfs[table_name] = pd.read_sql(f"SELECT * FROM {table_name}", src_conn)

    ##############################################################################################################
    #                                                                                                            
    #                                         4 - Connecting Output DB + Creating output DF                                                                                  #
    #                                                                                                                
    ############################################################################################################## 

        # Connecting Output DB
        
        print("4 - Connecting output DB + creating output DF")  
        dst_conn = sqlite3.connect(output_db)#connecting ouput DB -> creating if not exists
        dst_cur = dst_conn.cursor()#cursor creation towards output DB
           
        dst_cur.execute("PRAGMA foreign_keys = OFF;") #deactivate foreign keys constraints
        dst_cur.execute("BEGIN TRANSACTION")

        #Creating Df used to fill destination DB
        #Copy pasted datas -> just prepare it
        df_AIDACTIEL_dst = dfs['AIDACTIEL'] #dfs = dictionnary, we are takig here key AIDACTIEL
        
        df_CL_AIDE_ETAPE_CTRL_dst = dfs['CL_AIDE_ETAPE_CTRL']
        df_CL_AIDE_TYPE_CTRL_dst = dfs['CL_AIDE_TYPE_CTRL']

        #Datas can't be copy pasted, we create DF but empty

        df_CL_LAITCTRL_dst = dfs['CL_LAITCTRL'] 
        df_CL_LAITCTRL_dst.columns = df_CL_LAITCTRL_dst.columns #Recovering columns name
        df_CL_LAITCTRL_dst = pd.DataFrame(columns=df_CL_LAITCTRL_dst.columns)#Empty DF creation with column names

        df_CL_LAITEXPL_dst = dfs['CL_LAITEXPL']
        df_CL_LAITEXPL_dst.columns = df_CL_LAITEXPL_dst.columns
        df_CL_LAITEXPL_dst = pd.DataFrame(columns=df_CL_LAITEXPL_dst.columns)

        df_CL_LAITLACT_dst = dfs['CL_LAITLACT']
        df_CL_LAITLACT_dst.columns = df_CL_LAITLACT_dst.columns
        df_CL_LAITLACT_dst = pd.DataFrame(columns=df_CL_LAITLACT_dst.columns)

        df_EXPLOITATION_dst = dfs['EXPLOITATION']
        df_EXPLOITATION_dst.columns = df_EXPLOITATION_dst.columns
        df_EXPLOITATION_dst = pd.DataFrame(columns=df_EXPLOITATION_dst.columns)

        df_IDENTANV_dst = dfs['IDENTANV']
        df_IDENTANV_dst.columns = df_IDENTANV_dst.columns
        df_IDENTANV_dst = pd.DataFrame(columns=df_IDENTANV_dst.columns)

    ##############################################################################################################
    #                                                                                                            
    #                                         5 - Tables creation in output DB                                                                                     #
    #                                                                                                                
    ##############################################################################################################     
        
        print("5 - Tables creation in output DB") 
        Go_on_filling_output_tables = Creating_Out_DB(input_db,output_db)#Creating tables in output DB -> return true if OK

         # Index creation to speed up requests
        dst_cur.execute("CREATE INDEX IF NOT EXISTS idx_cl_noan ON CL_LAITLACT(NOAN)")
        dst_cur.execute("CREATE INDEX IF NOT EXISTS idx_ia_noan ON identanv(NOAN)")
        dst_cur.execute("CREATE INDEX IF NOT EXISTS idx_ia_nointsanit ON identanv(NOINTSANIT)")
        dst_cur.execute("CREATE INDEX IF NOT EXISTS idx_ex_nointexpl ON exploitation(NOINTEXPL)")
        dst_cur.execute("CREATE INDEX IF NOT EXISTS idx_ex_codpost ON exploitation(CODPOST)")
        
        dst_conn.commit()
    ##############################################################################################################
    #                                                                                                            
    #                                         6 - Assure data type consistency                                                                                  #
    #                                                                                                                
    ##############################################################################################################  
        if Go_on_filling_output_tables:
            
            #Assure la coherence des types de données
            
            print("6 - Data type consistency ")
            Data_type_consistency(dst_cur,dst_conn)

    ##############################################################################################################
    #                                                                                                            
    #                                         7 - Datas filling                                                                                     #
    #                                                                                                                
    ##############################################################################################################  
            
            print("7 - Datas Filling") 
    ##############################################################################################################
    # 7.1 Copy Pasted Tables
    ##############################################################################################################
            
            print("     7.1 - Filling tables (AIDACTIEL / CL_AIDE_ETAPE_CTRL / CL_AIDE_TYPE_CTRL)") 
            Go_on_tables_CC = Filling_CopyPasted_Tables(input_db,output_db,df_AIDACTIEL_dst,df_CL_AIDE_ETAPE_CTRL_dst,df_CL_AIDE_TYPE_CTRL_dst)
            df_AIDACTIEL_src_corrected = correct_ACTIEL_AIDACTIEL(dfs['AIDACTIEL'])
            
            df_IDENTANV_src_corrected = correct_ACTIEL_IDENTANV(dfs['IDENTANV'])
            df_AIDACTIEL_src_corrected.to_sql("AIDACTIEL", src_conn, if_exists="replace", index=False) #insert input DB
            df_IDENTANV_src_corrected.to_sql("IDENTANV", src_conn, if_exists="replace", index=False) #insert input DB

            if Go_on_tables_CC:
    ##############################################################################################################
    #7.2 Generating/Filling datas tables EXPLOITATION(farms creation) / IDENTANV(cows creation)
    ############################################################################################################## 
                  
                print("     7.2 - Filling generated datas (EXPLOITATION / IDENTANV)") 
                ##############################################################################################################
                    #7.2.1 Generating/Filling datas table EXPLOITATION(farms creation)
                ##############################################################################################################   
                   
                print("         7.2.1 Generation table EXPLOITATION")
                liste_generated_CP,liste_EXPLOITATION_NOTINTEXPL,go_on_exploitation,nb_fermes=Filling_exploitation()
                if go_on_exploitation:
                    #Table EXPLOITATION
                    
                    df_EXPLOITATION_dst["NOINTEXPL"] = liste_EXPLOITATION_NOTINTEXPL[0] #Remplir le champ NOINTEXPL du DATAFRAME de destination
                    df_EXPLOITATION_dst["CODPOST"] = liste_generated_CP #Remplir le champ CODPOST du DATAFRAME de destination
                    df_EXPLOITATION_dst= df_EXPLOITATION_dst[['NOINTEXPL', 'CODPOST']]
                
                    df_EXPLOITATION_dst.to_sql("EXPLOITATION", dst_conn, if_exists="replace", index=False) #insertion BDD dest
                    
                ##############################################################################################################
                    #7.2.2 Generating/Filling datas table IDENTANV(cows generation)
                ##############################################################################################################   
                    
                    print("         7.2.2 Generation table IDENTANV")
                    
                    go_on_identanv,df_IDENTANV_dst = Generate_IDENTANV(src_conn,dst_conn) #Filling DF output
                    df_IDENTANV_dst.to_sql("IDENTANV", dst_conn, if_exists="replace", index=False)#mettre a jour la BDD

                    if go_on_identanv:

    ##############################################################################################################
    # 7.3 Generating/fillinf datas tables  CL_LAITEXPL/CL_LAITLACT/CL/LAITCTRL
    ##############################################################################################################  
                        
                        print("     7.3 - Data generated (CL_LAITLACT / CL_LAIT_EXPL / CL_LAIT_CTRL)") 
                        ##############################################################################################################
                        # 7.3.1 Generating/filling data table CL_LAITEXPL
                        ##############################################################################################################   
                        
                        print("         7.3.1 Table Generation CL_LAITEXPL")
                        
                        go_on_CLLAITEXPL,liste_ID_LAITEXPL,liste_NOINTEXPL,liste_DATE_CTRL,liste_TRAIT1,liste_CD_TYPE_CTRL,liste_DATE_RECEPT_ANALYSE,liste_CD_ETAPE_CTRL = Generate_CLLAITEXPL(src_conn,dst_conn)

                        #FIlling DF
                        df_CL_LAITEXPL_dst['ID_LAITEXPL'] = liste_ID_LAITEXPL
                        df_CL_LAITEXPL_dst['NOINTEXPL'] = liste_NOINTEXPL
                        df_CL_LAITEXPL_dst['DATE_CTRL'] = liste_DATE_CTRL
                        df_CL_LAITEXPL_dst['TRAIT1'] = liste_TRAIT1
                        df_CL_LAITEXPL_dst['CD_TYPE_CTRL'] = liste_CD_TYPE_CTRL
                        df_CL_LAITEXPL_dst['DATE_RECEPT_ANALYSE'] = liste_DATE_RECEPT_ANALYSE
                        df_CL_LAITEXPL_dst['CD_ETAPE_CTRL'] = liste_CD_ETAPE_CTRL
                        df_CL_LAITEXPL_dst['CD_TYPE_CTRL'] = df_CL_LAITEXPL_dst['CD_TYPE_CTRL'].astype(int)

                        df_CL_LAITEXPL_dst.to_sql("CL_LAITEXPL", dst_conn, if_exists="replace", index=False)#mettre a jour la BDD
                        dst_conn.commit()

                        ##############################################################################################################
                        #7.3.2 Generating/ filling data table CL_LAILACT
                        ##############################################################################################################  
                        if go_on_CLLAITEXPL:
                            
                            print("         7.3.2 Table generation CL_LAITLACT")
                            go_ON_CLLAITLACT = False
                            
                            #Create DF avec CP/ACTIEL/NOLACT/nb lact/ proportion
                            #Exemple
                            #CP     ACTIEL      nb_lactation     proportion 
                            #1001     04            2               0.4
                            #1001     04            3               0.2
                            #1001     04            4               0.4
                            #1001     02            3               0.35
                            #1001     02            4               0.35
                            #1001     02            5               0.3
                            #1002     10            6               0.35
                            #1002     10            7               0.35
                            #1002     10            8               0.3

                            df_avg_lact_per_CP_per_actiel = recovery_nolact(src_cur) #df (CP/ACTIEL/avg(nombre_lactation)/proportion)


                            #Join between IDENTANV et EXPLOITATION in a df to have CODPOST for each cow in dst database and transform in 
                            df_IDENTANV_JOIN_EXPL_dst = pd.read_sql('Select * from IDENTANV ia JOIN EXPLOITATION ex ON ia.NOINTSANIT = ex.NOINTEXPL',dst_conn)

                            #Exemple :
                            #NOAN       SEXEAN      DTNAISANINV     NOINTSANIT      ACTIEL      NOANPERE     NOANMERE   NOINTEXPL   CODPOST
                            #15994855      F            20210314       200139         04         99999493    99523596      200139     1001        
                            #15994856      F            20210314       200139         04         99999493    99523596      200139     1001        

                            # CAST ACTIEL and CODPOST as str in both used df
                            df_IDENTANV_JOIN_EXPL_dst['ACTIEL'] = df_IDENTANV_JOIN_EXPL_dst['ACTIEL'].astype(str).str.strip()
                            df_IDENTANV_JOIN_EXPL_dst['CODPOST'] = df_IDENTANV_JOIN_EXPL_dst['CODPOST'].astype(str).str.strip()
                            df_avg_lact_per_CP_per_actiel['ACTIEL'] = df_avg_lact_per_CP_per_actiel['ACTIEL'].astype(str).str.strip()
                            df_avg_lact_per_CP_per_actiel['CODPOST'] = df_avg_lact_per_CP_per_actiel['CODPOST'].astype(str).str.strip()

                            # Affect to each cows for identANV dest  a number of lactation by applying sample_nb_lact taking her CP and ACTIEL
                            #Exemple :
                            #NOAN       SEXEAN      DTNAISANINV     NOINTSANIT      ACTIEL      NOANPERE     NOANMERE   NOINTEXPL   CODPOST     Nblact
                            #15994855      F            20210314       200139         04         99999493    99523596      200139     1001        4
                            #15994856      F            20210314       200139         04         99999493    99523596      200139     1001        2

                            df_IDENTANV_JOIN_EXPL_dst['Nb_lact'] = df_IDENTANV_JOIN_EXPL_dst.apply(
                                lambda row: sample_nb_lact(
                                    row['CODPOST'], 
                                    row['ACTIEL'], 
                                    df_avg_lact_per_CP_per_actiel
                                ),
                                axis=1
                            )

                            #Calculated total count of lactation
                            Nb_LACT_total = nombre_total_lactation(df_IDENTANV_JOIN_EXPL_dst) #return a integer by counting nombre of lactation
                            df_IDENTANV_JOIN_EXPL_dst['Nb_lact'] = df_IDENTANV_JOIN_EXPL_dst['Nb_lact'].astype(int)#cast int (security)

                            #Index generation : array generatin starting at 3531047,step = 1 during Nb_LACT_total times
                            #[3531047,3531048,3531049,...]
                            liste_index = generate_index(Nb_LACT_total,3531047,1)

                            #genere NOAN et CLLAITLACT 
                            liste_NOAN_CLLAITLACT = generate_NOAN_NOLACT_CLLAITLACT(df_IDENTANV_JOIN_EXPL_dst) #retourne liste_NOAN et liste_NOLACT

                            #Fill destination DF and CL_LAITLact table for output DB known columns
                            df_CL_LAITLACT_dst["ID_LAITLACT"] = liste_index[0]
                            df_CL_LAITLACT_dst["NOAN"] = liste_NOAN_CLLAITLACT[0]
                            df_CL_LAITLACT_dst["NOLACT"] = liste_NOAN_CLLAITLACT[1]
                            df_CL_LAITLACT_dst.to_sql("CL_LAITLACT", dst_conn, if_exists="replace", index=False) #fill output DB

                            
                            ##############################################################################################################
                            # CL_LAITLACT -> DATE_VEL
                            ############################################################################################################## 

                            #return DF  for each CP, ACTIEL and NOLACT the lactation time and the proportion of occurence
                            #EXEMPLE
                            #CP     ACTIEL      NOLACT      avg(DATE between 2 VEL in months)     proportion
                            #1001       04          1                   10                          0.1
                            #1001       04          1                   11                          0.5
                            #1001       04          1                   12                          0.4
                            #1001       04          2                   10                          0.2
                            #1001       04          2                   11                          0.2
                            #1001       04          2                   12                          0.6
                            #       ....
    
                            avg_duree_lact_per_ACTIELCPNOLACT = avg_duree_lactation_per_ACTIEL_per_CP_per_NO_LACT(src_cur)

                            df_tmp = Fill_Date_Vel_Par_IDLACT(avg_duree_lact_per_ACTIELCPNOLACT) 

                            '''
                            print("df_tmp_final",df_tmp)
        ID_LAITLACT      NOAN       NOLACT ACTIEL   DATE_VEL DATE_TAR  CODPOST Date_naissance  duree_finale  duree_cumulee
0        3531061        13683956       1     04 2024-10-08     None     4700     2022-09-19            25             25
1        3531338        13688683       1     CM 2020-12-31     None     4900     2019-02-10            23             23
2        3531331        13720330       1     40 2022-04-03     None     4900     2021-03-09            13             13
3        3531414        13747621       1     02 2022-11-30     None     5000     2021-12-05            12             12
4        3531067        13764917       1     04 2024-06-07     None     4700     2022-03-20            27             27
..           ...       ...     ...    ...        ...      ...      ...            ...           ...            ...
583      3531070        19591507       1     04 2024-03-05     None     4700     2021-12-16            27             27
584      3531071        19591507       2     04 2025-02-28     None     4700     2021-12-16            12             39
585      3531072        19591507       3     04 2026-02-23     None     4700     2021-12-16            12             51
586      3531073        19591507       4     04 2027-02-18     None     4700     2021-12-16            12             63
587      3531074        19591507       5     04 2028-02-13     None     4700     2021-12-16            12             75
                            '''

                            df_CL_LAITLACT_dst = pd.read_sql("SELECT * FROM CL_LAITLACT ORDER BY ID_LAITLACT", dst_conn) #assure order consistency
                            df_tmp.sort_values(by=["ID_LAITLACT"])#assure order consistency

                            # Merge to allign by ID_LAITLACT
                            df_CL_LAITLACT_dst = df_CL_LAITLACT_dst.merge(
                            df_tmp[["ID_LAITLACT", "DATE_VEL"]], 
                            on="ID_LAITLACT", 
                            how="left",
                            suffixes=("_old", "")
                            )

                            # Delete old column DATE_VEL_old(was empty)
                            if "DATE_VEL_old" in df_CL_LAITLACT_dst.columns:
                                df_CL_LAITLACT_dst = df_CL_LAITLACT_dst.drop(columns=["DATE_VEL_old"])

                            # Save in output DB
                            df_CL_LAITLACT_dst.to_sql("CL_LAITLACT", dst_conn, if_exists="replace", index=False)
                            
                            ##############################################################################################################
                            # CL_LAITLACT -> DATE_TAR
                            ############################################################################################################## 

                            #retourne un DF avec pour chaque vache la durée entre DATE_VEL et DATE_TAR par CP et par race et par NO_LACT 
                            #EXEMPLE
                            
                            avg_duree_VEL_TAR_per_ACTIELCPNOLACT = avg_duree_VEL_TAR_per_ACTIEL_per_CP_per_NO_LACT(src_cur)
                            
                            #Generate DATE_TAR from random choice duration between VEL and TAR and from DATE VEL Defined previously in output DB
                            df_tmp2 = Generate_DATE_TAR(avg_duree_VEL_TAR_per_ACTIELCPNOLACT,df_tmp)

                            df_tmp2 = df_tmp2.sort_values(by=["ID_LAITLACT"])
                        
                            # Merge
                            df_CL_LAITLACT_dst = df_CL_LAITLACT_dst.merge(
                                df_tmp2[["NOAN","NOLACT","DATE_TAR"]], 
                                on=["NOAN", "NOLACT"], 
                                how="left",
                                suffixes=("_old", "")
                            )

                            # Delete old DATE_TAR if exist
                            if "DATE_TAR_old" in df_CL_LAITLACT_dst.columns:
                                df_CL_LAITLACT_dst = df_CL_LAITLACT_dst.drop(columns=["DATE_TAR_old"])

                            # Reorganized columns order
                            colonnes_debut = ["ID_LAITLACT", "NOAN", "NOLACT", "DATE_VEL", "DATE_TAR"]
                            autres_colonnes = [col for col in df_CL_LAITLACT_dst.columns if col not in colonnes_debut]
                            df_CL_LAITLACT_dst = df_CL_LAITLACT_dst[colonnes_debut + autres_colonnes]
                            # Save in DB
                            df_CL_LAITLACT_dst.to_sql("CL_LAITLACT", dst_conn, if_exists="replace", index=False)
                            
                            # Case when DATE_TAR(NOLACT = 1) > a DATE_VEL(NOLACT =2) -> bo sense -> assure 2 months between DATE_Tar N et DATE_VEL N-1
                       

                            dst_cur.execute("""
                            UPDATE CL_LAITLACT
                            SET DATE_TAR = (
                                SELECT date(t2.DATE_VEL, '-2 months')
                                FROM CL_LAITLACT t2
                                WHERE t2.NOAN = CL_LAITLACT.NOAN 
                                AND t2.NOLACT = CL_LAITLACT.NOLACT + 1
                            )
                            WHERE EXISTS (
                                SELECT 1
                                FROM CL_LAITLACT t2
                                WHERE t2.NOAN = CL_LAITLACT.NOAN 
                                AND t2.NOLACT = CL_LAITLACT.NOLACT + 1
                                AND CL_LAITLACT.DATE_TAR >= t2.DATE_VEL
                            );
                            """)
                            dst_conn.commit()

                            #Date consistency
                            dst_cur.execute("""
                            UPDATE CL_LAITLACT
                            SET DATE_VEL = DATE(DATE_VEL),
                                DATE_TAR = DATE(DATE_TAR);
                            """)
                            dst_conn.commit()

                            #delete lines where DATE VEL > today
                            dst_cur.execute("""PRAGMA foreign_keys = OFF;""")
                            dst_cur.execute("""
                            DELETE FROM CL_LAITLACT
                            WHERE DATE(DATE_VEL) >= DATE('now');
                                            """)
                            dst_conn.commit()

                            # NULL if DATE_TAR > TODAY (ongoing lactation

                            dst_cur.execute("""UPDATE CL_LAITLACT
                            SET DATE_TAR = NULL
                            WHERE DATE_TAR > DATE('now');""")
                            dst_conn.commit()                            
                            df_CL_LAITLACT_dst = pd.read_sql("select * from CL_LAITLACT",dst_conn)
                            
                            


                        else:#go on cllaitexpl
                            dst_cur.execute("PRAGMA foreign_keys = ON;")
                            src_conn.close()
                            dst_conn.close()
                    else:#Go_on_exploitation
                        dst_cur.execute("PRAGMA foreign_keys = ON;")
                        src_conn.close()
                        dst_conn.close()
            else:#Go_on_tables_CC
                dst_cur.execute("PRAGMA foreign_keys = ON;")
                
                src_conn.close()
                dst_conn.close()
        else:# Go_on_filling_output_tables
            dst_cur.execute("PRAGMA foreign_keys = ON;")
            src_conn.close()
            dst_conn.close()

    else:#Go_on_Suppression
        pass
    
