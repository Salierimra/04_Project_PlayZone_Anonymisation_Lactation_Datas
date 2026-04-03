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


def Remplir_Tables_Copiées_collées(src_db,dst_db,df_AIDACTIEL_dst,df_CL_AIDE_ETAPE_CTRL_dst,df_CL_AIDE_TYPE_CTRL_dst):

    '''
    Cette fonction prend en paramètre :
    -   la connexion vers la db source
    -   La connexion vers la db destination
    -   un Dataframe comprenant les données de la BDD source pour la table AIDACTIEL
    -   un Dataframe comprenant les données de la BDD source pour la table CL_AIDE_ETAPE_CTRL
    -   un Dataframe comprenant les données de la BDD source pour la table CL_AIDE_TYPE_CTRL

    Cette fonction va remplir la BDD de destination à l'aide des Dataframe rentrés en paramètre

    Cette fonction return un boolean donnant l'information si tout s'est bien passé ou non
    '''
    Go_on = True
    with sqlite3.connect(src_db, timeout=30) as src_conn, \
        sqlite3.connect(dst_db, timeout=30) as dst_conn:

        df_AIDACTIEL_dst.to_sql("AIDACTIEL", dst_conn, if_exists="append", index=False) 
        df_CL_AIDE_ETAPE_CTRL_dst.to_sql("CL_AIDE_ETAPE_CTRL", dst_conn, if_exists="append", index=False)
        df_CL_AIDE_TYPE_CTRL_dst.to_sql("CL_AIDE_TYPE_CTRL", dst_conn, if_exists="append", index=False)  
            
    return Go_on

def correct_ACTIEL_AIDACTIEL(df):
    '''
    Fonction prenant en input un df (le Dataframe ACTIEL_src)
    Fonction permettant d'assurer le bon type de données dans champ ACTIEL de la table AIDACTIEL
    Mettre dans la BDD que ACTIEL est un VARCHAR(si ce n'est pas le cas) et qu'il est sous la forme 01,02,10,11,XM,XL
    Fonction retournant le df source corrigé pret à être mis dans la BDD
    '''
    liste_actiel = df['ACTIEL'] #recuperer les données du DF 
    liste_actiel_ok=[]
    
    for actiel in liste_actiel: #on parcourt les elements
        
        try: #try conversion en int -> crash si actiel = XM XL,...
            if len(str(actiel))==4 and str(actiel).find('.')!=-1: #10.0
                
                actiel_ok = str(int(actiel))
                
            elif len(str(actiel))==3 and str(actiel).find('.')!=-1: #8.0
                
                actiel_ok = "0"+str(int(actiel))
                
        
            else:#10
                actiel_ok = actiel
        except ValueError:#XM
            actiel_ok = actiel

        finally:
            liste_actiel_ok.append(actiel_ok)#ajoute l'element corrigé à une liste
    
    
    df['ACTIEL'] = liste_actiel_ok #modifie le DF AIDACTIEL (champ ACTIEL) source
    return df


def correct_ACTIEL_IDENTANV(df):
    '''
    Fonction prenant en input un df (le Dataframe IDENTANV_src)
    Fonction permettant d'assurer le bon type de données dans champ ACTIEL de la table AIDACTIEL
    Mettre dans la BDD que ACTIEL est un VARCHAR et qu'il est sous la forme 01,02,10,11,XM,XL
    Fonction retournant le df source corrigé pret à être mis dans la BDD
    '''
    liste_actiel = df['ACTIEL'] #recuperer les données du DF 
    liste_actiel_ok=[]
    
    
    for actiel in liste_actiel: #on parcourt les elements
        
        try: #try conversion en int -> crash si actiel = XM XL,...
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
            
            liste_actiel_ok.append(actiel_ok)#ajoute l'element corrigé à une liste
            
    
    df['ACTIEL'] = liste_actiel_ok #modifie le DF AIDACTIEL (champ ACTIEL) source
    
    return df







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
    #                                         7 - Insertion des données                                                                                     #
    #                                                                                                                
    ##############################################################################################################  
            
            print("7 - Insertion des données") 
    ##############################################################################################################
    # 7.1 Insertion des données copiées collées de la source vers la destination
    ##############################################################################################################
            
            print("     7.1 - Insertion des données sans modification (AIDACTIEL / CL_AIDE_ETAPE_CTRL / CL_AIDE_TYPE_CTRL)") 
            Go_on_tables_CC = Remplir_Tables_Copiées_collées(input_db,output_db,df_AIDACTIEL_dst,df_CL_AIDE_ETAPE_CTRL_dst,df_CL_AIDE_TYPE_CTRL_dst)
            df_AIDACTIEL_src_corrected = correct_ACTIEL_AIDACTIEL(dfs['AIDACTIEL'])
            
            df_IDENTANV_src_corrected = correct_ACTIEL_IDENTANV(dfs['IDENTANV'])
            df_AIDACTIEL_src_corrected.to_sql("AIDACTIEL", src_conn, if_exists="replace", index=False) #insertion BDD source
            df_IDENTANV_src_corrected.to_sql("IDENTANV", src_conn, if_exists="replace", index=False) #insertion BDD source
  
        else:# Go_on_filling_output_tables
            dst_cur.execute("PRAGMA foreign_keys = ON;")
            src_conn.close()
            dst_conn.close()
    else:#Go_on_Suppression
        pass
    
