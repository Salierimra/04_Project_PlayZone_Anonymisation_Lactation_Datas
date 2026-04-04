# Project-PlayZone Technobel-Anonymisation-données-lactation

## Project Description

This project was developed for Eleveo with the objective of generating synthetic lactation data that closely resembles real-world datasets while ensuring proper anonymization.

To achieve this, a Python script is used to read the production database, extract key statistical characteristics, and generate new data that preserves the original distributions and proportions.

## Project Goal

The project aims to:

- Ensure full anonymization of real data
- Preserve statistical properties such as mean and standard deviation for all lactation parameters
- Generate a SQLite database that maintains the original data distribution and proportions

## Key Questions

- Is the generated data fully anonymized?
- Does the generated data accurately preserve the statistical characteristics of the original dataset?

## Technologies Used

- Sqlite 3 Database
- Python (sk-learn)
- Power BI
  
## Project phases

### EDA

This section outlines the most significant statistical findings derived from the Exploratory Data Analysis (EDA) phase.

65% of the alive cows belong to breed "4".

<img width="1103" height="742" alt="image" src="https://github.com/user-attachments/assets/64c499c0-ba7b-4947-be31-30a778cfe8cd" />

Lact quantity per laction follows a normal distribution

<img width="1152" height="753" alt="image" src="https://github.com/user-attachments/assets/a4c8a815-cff3-4d51-b92d-9d4d7d4e0223" />

Number of lactation for each alive cows

<img width="1162" height="747" alt="image" src="https://github.com/user-attachments/assets/c91a3db3-fddf-4605-8561-e34f3d9d60a9" />

### Data Collection

Sqlite Database provided by Client

### Data Cleaning

N/A in this project

### Copy Pasted table

Three tables are directly copied from the input database to the output database:

- Breed: contains all breeds present in the database
- ETAPE_CTRL_TEST: contains all possible steps in a lactation control process
- CTRL_TYPE: contains all possible types of lactation control

### Generated Datas

Two Tables must be generated in order to assure anonymyzation :

#### EXPLOITATION

Creating number of farms desired with respect to input database repartition concerning municipality (first two number in postal code -> https://fr.wikipedia.org/wiki/Code_postal_en_Belgique)

##### Input DB

<img width="1012" height="467" alt="image" src="https://github.com/user-attachments/assets/ab11e498-99c9-4f60-92fb-e0ae998dbfd7" />

##### Output generated datas

<img width="1012" height="467" alt="image" src="https://github.com/user-attachments/assets/b3a27747-c2d0-413e-b28b-0d4f2c57d9c4" />

#### IDENTANV

Creating number of farms desired with respect to input database repartition concerning number of cows per Postal code and per herd

##### Input DB

<table>
  <tr>
    <td><img width="528" alt="image" src="https://github.com/user-attachments/assets/ed66ee64-fe98-46b9-8590-c3466727171e" /></td>
    <td><img width="528" alt="image" src="https://github.com/user-attachments/assets/9eb6f71a-2937-4f77-ae49-2595ff5e3607" /></td>
  </tr>
</table>

##### Output generated datas

### Datawarehouse 



### Deep Learning

#### Feature engineering


#### Feature selection



#### Results



### DashBoard



## Findings /insights



## Flask -  Using DL Model with local html page

### Use



