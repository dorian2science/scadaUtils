# Log new features
What's new in V1.7 ?
--------------
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
