# -*- coding: utf-8 -*-

from qgis.core import QGis, QgsVectorLayer, QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsField, QgsGeometry, QGis, QgsSimpleMarkerSymbolLayerV2, QgsLineSymbolV2, QgsMarkerSymbolV2, QgsMarkerLineSymbolLayerV2, QgsSimpleMarkerSymbolLayerBase, QgsSingleSymbolRendererV2,QgsAbstractGeometryV2
from PyQt4.QtGui import QIcon, QAction, QColor
from PyQt4.QtCore import QObject, SIGNAL, QVariant
from PyQt4.QtSql import QSqlDatabase, QSqlQuery
import resources_rc  
from qgis.gui import QgsMessageBar

class StartNotSimple:

    def __init__(self, iface):
        
        self.iface = iface

        self.tableSchema = 'edgv'
        self.geometryColumn = 'geom'
        self.keyColumn = 'id'

    def initGui(self): 
        # cria uma ação que iniciará a configuração do plugin 
        pai = self.iface.mainWindow()
        icon_path = ':/plugins/StartNotSimple/icon.png'
        self.action = QAction (QIcon (icon_path),u"Acessa banco de dados para revisão de Geometria Simples", pai)
        self.action.setObjectName ("Stard database")
        self.action.setStatusTip(None)
        self.action.setWhatsThis(None)
        self.action.triggered.connect(self.run)
        # Adicionar o botão icone
        self.iface.addToolBarIcon (self.action) 
        #Cria uma nova toolbar
        #self.toolbar = self.iface.addToolBar(u'Validation Tool')
        #self.toolbar.addAction(self.action)
    def unload(self):
        # remove o item de ícone do QGIS GUI.
        self.iface.removeToolBarIcon (self.action)
        
        
    def run(self):

    ##################################
    ###### PEGA A LAYER ATIVA ########
    ##################################

        layer = self.iface.activeLayer() 

        if not layer:
            self.iface.messageBar().pushMessage("Erro", u"Esperando uma Active Layer!", level=QgsMessageBar.CRITICAL, duration=4)
            return
        if layer.featureCount() == 0:
            self.iface.messageBar().pushMessage("Erro", u"a camada não possui feições!", level=QgsMessageBar.CRITICAL, duration=4)
            return

        parametros = layer.source().split(" ") # recebe todos os parametros em uma lista ( senha, porta, password etc..)

    ####################################
    ###### INICIANDO CONEXÃO DB ########
    ####################################

        # Outra opção para isso, seria usar ex: self.dbname.. self.host.. etc.. direto dentro do laço for.
        dbname = "" 
        host = ""
        port = 0
        user = ""
        password = ""

        for i in parametros:
            part = i.split("=")
            
        # Recebe os parametros guardados na própria Layer

            if "dbname" in part[0]:
                dbname = part[1].replace("'", "")

            elif "host" in part[0]:
                host = part[1].replace("'", "")

            elif "port" in part[0]:
                port = int(part[1].replace("'", ""))

            elif "user" in part[0]:
                user = part[1].replace("'", "")

            elif "password" in part[0]:
                password = part[1].split("|")[0].replace("'", "")

        print dbname, host, port, user, password

        # Testa se os parametros receberam os valores pretendidos, caso não, apresenta a mensagem informando..
        if len(dbname) == 0 or len(host) == 0 or port == 0 or len(user) == 0 or len(password) == 0:
            self.iface.messageBar().pushMessage("Erro", u'Um dos parametros não foram devidamente recebidos!', level=QgsMessageBar.CRITICAL, duration=4)
            return

    ####################################
    #### SETA VALORES DE CONEXÃO DB ####
    ####################################

        connection = QSqlDatabase.addDatabase('QPSQL')
        connection.setHostName(host)
        connection.setPort(port)
        connection.setUserName(user)
        connection.setPassword(password)
        connection.setDatabaseName(dbname)

        if not connection.isOpen(): # Testa se a conexão esta recebendo os parametros adequadamente.
            if not connection.open():
                print 'Error connecting to database!'
                self.iface.messageBar().pushMessage("Erro", u'Error connecting to database!', level=QgsMessageBar.CRITICAL, duration=4)
                print connection.lastError().text()
                return

    ####################################
    ###### CRIAÇÃO DE MEMORY LAYER #####
    ####################################
        

        layerCrs = layer.crs().authid() # Passa o formato (epsg: numeros)

        flagsLayerName = layer.name() + "_flags"
        flagsLayerExists = False

        for l in QgsMapLayerRegistry.instance().mapLayers().values(): # Recebe todas as camadas que estão abertas
            if l.name() == flagsLayerName: # ao encontrar o nome pretendido..
                self.flagsLayer = l # flagslayer vai receber o nome..
                self.flagsLayerProvider = l.dataProvider()
                flagsLayerExists = True # se encontrado os parametros buscados, recebe True.
                break
        
        if flagsLayerExists == False: # se não encontrado os parametros buscados, recebe False.
            tempString = "Point?crs="
            tempString += str(layerCrs)

            self.flagsLayer = QgsVectorLayer(tempString, flagsLayerName, "memory")
            self.flagsLayerProvider = self.flagsLayer.dataProvider()
            self.flagsLayerProvider.addAttributes([QgsField("id", QVariant.Int), QgsField("geomId", QVariant.String), QgsField("motivo", QVariant.String)])
            self.flagsLayer.updateFields()

        self.flagsLayer.startEditing()
        ids = [feat.id() for feat in self.flagsLayer.getFeatures()]
        self.flagsLayer.deleteFeatures(ids)
        self.flagsLayer.commitChanges()
        
        lista_fid = [] # Iniciando lista
        for f in layer.getFeatures():
            lista_fid.append(str(f.id())) # Guarda na lista. A lista de Feature ids passa tipo "int", foi convertido e guardado como "str".

        source = layer.source().split(" ")
        self.tableName = " " # Inicia vazio
        layerExistsInDB = False
        
        for i in source:
                
            if "table=" in i or "layername=" in i: # Se encontrar os atributos pretendidos dentre todos do for
                self.tableName = source[source.index(i)].split(".")[1] # Faz split em ponto e pega a segunda parte.
                self.tableName = self.tableName.replace('"', '')
                layerExistsInDB = True
                break
             
        if layerExistsInDB == False:
            self.iface.messageBar().pushMessage("Erro", u"Provedor da camada corrente não provem do banco de dados!", level=QgsMessageBar.CRITICAL, duration=4)
            return

        ##############################
        #### Busca através do SQL ####
        ##############################


        sql = """select foo."{3}" as "{3}", ST_AsText(ST_MULTI(st_startpoint(foo."{2}"))) as "{2}" from (
        select "{3}" as "{3}", (ST_Dump(ST_Node(ST_SetSRID(ST_MakeValid("{2}"),ST_SRID("{2}"))))).geom as "{2}" from "{0}"."{1}"  
        where ST_IsSimple("{2}") = 'f' and {3} in ({4})) as foo where st_equals(st_startpoint(foo."{2}"),st_endpoint(foo."{2}"))""".format(self.tableSchema, self.tableName, self.geometryColumn, self.keyColumn, ",".join(lista_fid))
            
        query = QSqlQuery(sql)

        self.flagsLayer.startEditing()
        flagCount = 0 # iniciando contador que será referência para os IDs da camada de memória.

        listaFeatures = []
        while query.next():

            
            id = query.value(0) # recebendo valores buscados no sql
            local = query.value(1) # recebendo valores buscados no sql
            motivo = query.value(2)
            print local, id, motivo
           
            flagId = flagCount

            flagFeat = QgsFeature()
	    flagFeat.setFields(self.flagsLayer.fields()) # passa quais atributos serão usados.
            flagGeom = QgsGeometry.fromWkt(local) # passa o local onde foi localizado o erro.
            flagFeat.setGeometry(flagGeom)
            flagFeat.setAttribute(0, flagId) # insere o id definido para a coluna 0 da layer de memória.
            flagFeat.setAttribute(1, id) # insere o id da geometria para a coluna 1 da layer de memória.
            flagFeat.setAttribute(2,  u"A geometria não é simples.")
            listaFeatures.append(flagFeat)    

            flagCount += 1 # incrementando o contador a cada iteração

        self.flagsLayerProvider.addFeatures(listaFeatures)
        self.flagsLayer.commitChanges() # Aplica as alterações à camada.
        
        QgsMapLayerRegistry.instance().addMapLayer(self.flagsLayer) # Adicione a camada no mapa
       
        if flagCount == 0: 
            
            QgsMapLayerRegistry.instance().removeMapLayer(self.flagsLayer.id())
            self.iface.messageBar().pushMessage("Aviso", u"Não foi encontrado Flags em \"" + layer.name() + "\" !", level=QgsMessageBar.CRITICAL, duration=4)

            return
        if len(query.lastError().text()) == 1:
            self.iface.messageBar().pushMessage("Aviso", "foram geradas " + str(flagCount) + " flags para a camada \"" + layer.name() + "\" !", level=QgsMessageBar.INFO, duration=4)
        else:
            self.iface.messageBar().pushMessage("Erro", u"a geração de flags falhou!", level=QgsMessageBar.CRITICAL, duration=4)
            print query.lastError().text()
