# Log new features
What's new in V2.1 ?
--------------
### v2.3
- onglet dataPa : bouton à cocher "greenlight" pour rejouer le live des essais DSP et voir la répartition des tensions cellules en déplacant le curseur temporel. Les données clés temps réel ont été aussi ajoutéessu beta_usr

### v2.2
- onglet dataset : bouton à cocher "greenlight" pour rejouer le live des essais AVL et voir la répartition des tensions cellules en déplacant le curseur temporel.   
### v2.1
- display panel(a video explaining how to interact to use the options is available [here](https://inocel.atlassian.net/wiki/spaces/Diagnostiq/pages/143392794/Utilisation+de+l+onglet+display+panel)) :
    - layout of widgets more fluid   
    - arrange signals on different subplots(rows and columns) and change the layout.
    - change the units/axes of a signal
    - change the name of the signal(**label**)
    - possible to save/load a "planche" : which is a configuration of signal:color, unit, column and row subplot id, and label.    
    - resizing figure and elements on the figure responsive
    - adjust the number of ticks of the axes
    - adjust the font size of axes
- request tabs:  
### v1.10
- [possible to drag-drop files](https://inocel.atlassian.net/wiki/spaces/Diagnostiq/pages/135757872/Charger+un+fichier+de+donn+es) of pre-defined format for bench\_crio, AVL, cea_pacmat. 

### v1.9
- god mode tab available for futur in-depth analysis
- get state machine report available to [debug state machine](https://inocel.atlassian.net/wiki/spaces/Diagnostiq/pages/132481048/Obtenir+un+rapport+des+tats+de+la+machine+d+tat+du+syst+me) 
### v1.8
- dataset tab is available. 
- Possible to drag and drop data as a csv file(works only if the csv is correctly formated) to visualize it.
- change x-axis is in the **display panel** and it is very fast. 
- all axes are by default blacks
- resize the figure in the **display panel** 
- button *delete all* to empty the table of tags. 
### v1.7
- CS-514 Gaia - Ajouter la possibilité d'exporter les signaux tracés avec leur code couleur. Il s'agit de pouvoir [sauvegarder une planche de tags avec leur code couleur](https://inocel.atlassian.net/wiki/spaces/Diagnostiq/pages/123535485/Importer+les+signaux+trac+s+avec+leur+code+couleur). 
- possibilité d'utiliser la fonction ["Compare multiple HOVER"](https://inocel.atlassian.net/wiki/spaces/Diagnostiq/pages/123568158/Compare+multiple+HOVER)
### v1.6
- CS-512 Gaia - Protéger le champ de résolution temporelle -- implémenté
### v1.5
- If missing data or if there is a bug an alert will pop up.
### v1.4
- possible to create new variables by doing some simple computations in the tab **processing**.
### v1.3
- possible to chose the model. Model z92 is available!
- the range of possible datetimes is automatically according to the availability of the data for model selected.
### v1.2
- panel **parameters**: check button  *Use coarse data* check button available to speed up the request of data. The "coarse data" are resampled at 10s so it does not make any sense to select a resampling rate bellow this value.
- panel **dispay** : remove gaps can be based on the current (I>1). To use this option instead of "no data" it is necessary to load CurrentPV.
- by default/at start the last 7 days are loaded.
### v1.1
- change color of each trace
- 4 tabs instead of only one panel settings:
    - data_parameters : select the data variables,time window, resampling rate...
    - models : selection of model
    - display : display features
    - processing : compute new variables
- display tab
    - pretty axes automatically positionned
    - change background color
    - change marker size
    - change number of digits of the value in hover mode
    - change the font size of hover text.
    - the unit is displayed in the hover value text.
    - show the grid(not fully done on the y axis)
- resize horizontally the settings panel
