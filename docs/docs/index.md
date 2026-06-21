# legacy_pipe documentation!

## Description

Pipeline for processing legacy neuroimages

### Preprocessing

* includes preprocessing of scans from different sites and broad aquisituin range
* This pipeline starts with the raw files (dcm)
Assumptions: 
1. Can't assume the files are organized in folders by subjects and session. Therefore it includes metadata reading, editing and organizing
2. The raw scans are not yet annonimized. This is necessary to validate the identity of the subjects (a challenging process specifically when working with legacy scans) due to typos. It creates and works with a json file containg all subjects' personal details, it's stored in a data folder, with subfolders raw, interim, external, processed, and step3_manual_cleaning containing the manual work for each data source. Due to confidentiality concerns, it is not in github, but assumes you have such directory to read and write files with confidential personal information.

### Analysis

* Includes notebooks for: 
Raw results and metadata interpretation, different statistical modeling, power analysis, permutation testing, coefficient stability, harmonization testing and debugging.  

