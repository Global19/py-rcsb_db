#
# File:    SchemaDefReShape.py
# Author:  J. Westbrook
# Date:    4-Aug-2018
#
#
# Updates:
#    15-Aug-2018 jdw add next() method for py2 compatibility
#    16-Aug-2018 jdw add remaining layouts for sliced schema
##
"""
Companion class to reshape data objects produced by SchemaDefDataPrep()

"""
__docformat__ = "restructuredtext en"
__author__ = "John Westbrook"
__email__ = "jwest@rcsb.rutgers.edu"
__license__ = "Apache 2.0"

import copy
import itertools
import logging

logger = logging.getLogger(__name__)


class SliceValues(object):
    """Iterator class for parent slice values.
    """

    def __init__(self, schemaDataDictById, schemaDefObj, sliceFilter):
        self.__sD = schemaDefObj
        spiL = self.__sD.getSliceParentItems(sliceFilter)
        spfL = self.__sD.getSliceParentFilters(sliceFilter)
        vD = {}
        for sp in spiL:
            catId = sp['CATEGORY']
            atId = sp['ATTRIBUTE']
            vals = []
            if catId in schemaDataDictById:
                for rowD in schemaDataDictById[catId]:
                    if self.__testFilter(rowD, catId, spfL):
                        vals.append(((catId, atId), rowD[atId]))
            vD[(catId, atId)] = vals
        #
        self.index = 0
        logger.debug("Parent value dict %r" % vD.items())
        # Make a list of lists and then get the product
        #
        valueL = []
        for ky, vL in vD.items():
            valueL.append(vL)
        self.data = list(itertools.product(*valueL))
        logger.debug("Parent value product list %r" % self.data)

    def __testFilter(self, rowD, catId, filters):
        ok = True
        for filter in filters:
            if catId != filter['CATEGORY']:
                ok = False
                break
            if filter['ATTRIBUTE'] in rowD and rowD[filter['ATTRIBUTE']] in filter['VALUES']:
                continue
            else:
                ok = False
                break

        return ok

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        try:
            result = self.data[self.index]
            self.index += 1
        except IndexError:
            raise StopIteration
        return result

    def __prev__(self):
        self.index -= 1
        if self.index < 0:
            raise StopIteration
        return self.data[self.index]


class SchemaDefReShape(object):

    """Companion class to reshape data objects produced by SchemaDefDataPrep()
    """

    def __init__(self, schemaDefAccessObj, workPath=None, verbose=True):
        self.__verbose = verbose
        self.__workPath = workPath
        self.__debug = False
        self.__sD = schemaDefAccessObj
        #

    def applyShape(self, schemaDataDictById, styleType="rowwise_by_name"):
        """
        """
        return self.__reshapeSchemaData(schemaDataDictById, styleType=styleType)

    def applySlicedShape(self, schemaDataDictById, styleType="rowwise_by_name", logSize=False, sliceFilter=None):
        """
        """
        rL = []
        if sliceFilter:
            rL = []
            sliceIndex = self.__sD.getSliceIndex(sliceFilter)
            logger.debug("Slice index %r" % sliceIndex)
            #
            #
            sliceValues = SliceValues(schemaDataDictById, self.__sD, sliceFilter)
            #
            flagNew = True
            # JDW : TEMP ---------- ----------
            if styleType == "rowwise_by_name_with_cardinality" and flagNew:
                logger.debug("Invoking one-pass slice filter %s" % sliceFilter)
                rL = self.__sliceRowwiseByNameWithCardOnePass(schemaDataDictById, sliceFilter, sliceIndex)
                logger.debug("Completed one-pass slice filter %s" % sliceFilter)
            else:
                # JDW : TEMP ---------- ----------
                for ii, sliceValue in enumerate(sliceValues):
                    logger.debug(" %4d filter %s slice value %r" % (ii, sliceFilter, sliceValue))
                    rD = self.__reshapeSlicedSchemaData(schemaDataDictById, sliceFilter, sliceValue, sliceIndex, styleType=styleType)
                    logger.debug("rD keys %s" % (rD.keys()))
                    rL.append(rD)
        else:
            return [self.__reshapeSchemaData(schemaDataDictById, styleType=styleType)]

        return rL

    def __reshapeSlicedSchemaData(self, schemaDataDictById, sliceFilter, sliceValues, sliceIndex, styleType="rowwise_by_name"):
        """  Reorganize and rename input table data object according to the input style preference:

             Input: schemaDataDictById  (styleType="rowwise_by_id")
                                         dict[<schemaId>]   = [ row1asDict[attributeId]=value,  row2asDict[attribute]=value, .. ]

             Output: rowwise_by_name:     dict[<schemaObjName>] = [ row1Dict[attributeName]=value,  row2dict[], .. ]
                     rowwise_no_name:    dict[<schemaObjName>] = {'attributes': [atName1, atName2,... ], 'data' : [[val1, val2, .. ],[val1, val2,... ]]}
                     columnwise_by_name: dict[<schemaObjName>] = {'atName': [val1, val2,... ], atName2: [val1,val2, ... ], ...}
      rowwise_by_name_with_cardinality:  same as rowwise_byName with special handing of tables with unit cardinality
                                                          dict[<schemaObjName>] = row1Dict[attributeName]=value (singleton row)
        """
        rD = {}
        try:
            if styleType == "rowwise_by_name":
                rD = self.__sliceRowwiseByName(schemaDataDictById, sliceFilter, sliceValues, sliceIndex)
            elif styleType == "rowwise_by_name_with_cardinality":
                rD = self.__sliceRowwiseByNameWithCard(schemaDataDictById, sliceFilter, sliceValues, sliceIndex)
            elif styleType == "columnwise_by_name":
                rD = self.__sliceColumnwise(schemaDataDictById, sliceFilter, sliceValues, sliceIndex)
            elif styleType == "rowwise_no_name":
                rD = self.__shapeRowwiseNoName(schemaDataDictById)
            elif styleType == "rowwise_by_id":
                rD = schemaDataDictById
            else:
                rD = schemaDataDictById
                logger.warning("Unsupported style type %s" % styleType)
        except Exception as e:
            logger.exception("Failing with %s" % str(e))
            rD = schemaDataDictById

        return rD

    def __inSlice(self, schemaId, sliceIndex, rowD, parentVals):
        """ Test if the child values in the input row dictionary equal the corresponding input parents values
        """
        ok = True
        try:
            if schemaId in sliceIndex:
                for parentVal in parentVals:
                    if parentVal[0] in sliceIndex[schemaId]:
                        # cAtId = sliceIndex[schemaId][parentVal[0]]
                        tOk = False
                        for cAtId in sliceIndex[schemaId][parentVal[0]]:
                            if cAtId in rowD and rowD[cAtId] == parentVal[1]:
                                tOk = True
                                break
                        if tOk:
                            continue
                        else:
                            ok = False
                            break
                    else:
                        ok = False
                        break
            else:
                ok = False

        except Exception as e:
            logger.exception("Failing with %s" % str(e))
            ok = False
        return ok

    def __sliceRowwiseByNameWithCard(self, schemaDataDictById, sliceFilter, sliceValues, sliceIndex):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            lExtra = schemaObj.isSliceExtra(sliceFilter)
            if lExtra:
                logger.debug("SchemaId %r slice extra %r" % (schemaId, lExtra))
            if schemaId not in sliceIndex and not schemaObj.isSliceExtra(sliceFilter):
                continue
            # ------
            schemaObjName = self.__sD.getSchemaName(schemaId)
            #
            iRowDList = schemaDataDictById[schemaId]

            #
            oRowDList = []
            for iRowD in iRowDList:
                if lExtra or self.__inSlice(schemaId, sliceIndex, iRowD, sliceValues):
                    oRowD = {}
                    for atId in iRowD:
                        oRowD[schemaObj.getAttributeName(atId)] = iRowD[atId]
                    oRowDList.append(oRowD)

            if (len(oRowDList) < 1) and not schemaObj.isMandatory():
                logger.debug("Schema id %r row length %r mandatory %r" % (schemaId, len(oRowDList), schemaObj.isMandatory()))
                continue

            if schemaObj.hasSliceUnitCardinality(sliceFilter) and len(oRowDList) == 1:
                rD[schemaObjName] = oRowDList[0]
            else:
                rD[schemaObjName] = oRowDList

        return rD

    def __sliceRowwiseByName(self, schemaDataDictById, sliceFilter, sliceValues, sliceIndex):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            lExtra = schemaObj.isSliceExtra(sliceFilter)
            if lExtra:
                logger.debug("SchemaId %r slice extra %r" % (schemaId, lExtra))
            if schemaId not in sliceIndex and not schemaObj.isSliceExtra(sliceFilter):
                continue
            # ------
            schemaObjName = self.__sD.getSchemaName(schemaId)
            #
            iRowDList = schemaDataDictById[schemaId]

            oRowDList = []
            for iRowD in iRowDList:
                if lExtra or self.__inSlice(schemaId, sliceIndex, iRowD, sliceValues):
                    oRowD = {}
                    for atId in iRowD:
                        oRowD[schemaObj.getAttributeName(atId)] = iRowD[atId]
                    oRowDList.append(oRowD)
            #
            if (len(oRowDList) < 1) and not schemaObj.isMandatory():
                logger.debug("Schema id %r row length %r mandatory %r" % (schemaId, len(oRowDList), schemaObj.isMandatory()))
                continue
            rD[schemaObjName] = oRowDList

        return rD

    def __sliceColumnwise(self, schemaDataDictById, sliceFilter, sliceValues, sliceIndex):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            lExtra = schemaObj.isSliceExtra(sliceFilter)
            if lExtra:
                logger.debug("SchemaId %r slice extra %r" % (schemaId, lExtra))
            if schemaId not in sliceIndex and not schemaObj.isSliceExtra(sliceFilter):
                continue
            # ------
            schemaObjName = self.__sD.getSchemaName(schemaId)
            iRowDList = schemaDataDictById[schemaId]
            #
            colD = {}
            for iRowD in iRowDList:
                if lExtra or self.__inSlice(schemaId, sliceIndex, iRowD, sliceValues):
                    for atId in iRowD:
                        atName = schemaObj.getAttributeName(atId)
                        if atName not in colD:
                            colD[atName] = []
                        colD[atName].append(iRowD[atId])

            if (len(colD) < 1) and not schemaObj.isMandatory():
                logger.debug("Schema id %r row length %r mandatory %r" % (schemaId, len(colD), schemaObj.isMandatory()))
                continue
            rD[schemaObjName] = colD

        return rD

    def __sliceRowwiseNoName(self, schemaDataDictById, sliceFilter, sliceValues, sliceIndex):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            lExtra = schemaObj.isSliceExtra(sliceFilter)
            if lExtra:
                logger.debug("SchemaId %r slice extra %r" % (schemaId, lExtra))
            if schemaId not in sliceIndex and not schemaObj.isSliceExtra(sliceFilter):
                continue
            # ------
            atIdList = self.__sD.getAttributeIdList(schemaId)
            atNameList = self.__sD.getAttributeNameList(schemaId)
            schemaObjName = self.__sD.getSchemaName(schemaId)
            #
            iRowDList = schemaDataDictById[schemaId]

            #
            oRowList = []
            for iRowD in iRowDList:
                if lExtra or self.__inSlice(schemaId, sliceIndex, iRowD, sliceValues):
                    oRowL = []
                    for atId in atIdList:
                        oRowL.append(iRowD[atId])
                    oRowList.append(oRowL)
            #
            if (len(oRowList) < 1) and not schemaObj.isMandatory():
                logger.debug("Schema id %r row length %r mandatory %r" % (schemaId, len(oRowList), schemaObj.isMandatory()))
                continue
            rD[schemaObjName] = {'attributes': atNameList, 'data': oRowList}

        return rD

    def __reshapeSchemaData(self, schemaDataDictById, styleType="rowwise_by_name"):
        """  Reorganize and rename input table data object according to the input style preference:

             Input: schemaDataDictById  (styleType="rowwise_by_id")
                                         dict[<schemaId>]   = [ row1asDict[attributeId]=value,  row2asDict[attribute]=value, .. ]

             Output: rowwise_by_name:    dict[<schemaObjName>] = [ row1Dict[attributeName]=value,  row2dict[], .. ]
                     rowwise_no_name:    dict[<schemaObjName>] = {'attributes': [atName1, atName2,... ], 'data' : [[val1, val2, .. ],[val1, val2,... ]]}
                     columnwise_by_name: dict[<schemaObjName>] = {'atName': [val1, val2,... ], atName2: [val1,val2, ... ], ...}
      rowwise_by_name_with_cardinality:  same as rowwise_byName with special handing of tables with unit cardinality
                                                          dict[<schemaObjName>] = row1Dict[attributeName]=value (singleton row)
        """
        rD = {}
        try:
            if styleType == "rowwise_by_name":
                rD = self.__shapeRowwiseByName(schemaDataDictById)
            elif styleType == "rowwise_by_name_with_cardinality":
                rD = self.__shapeRowwiseByNameWithCard(schemaDataDictById)
            elif styleType == "columnwise_by_name":
                rD = self.__shapeColumnwise(schemaDataDictById)
            elif styleType == "rowwise_no_name":
                rD = self.__shapeRowwiseNoName(schemaDataDictById)
            elif styleType == "rowwise_by_id":
                rD = schemaDataDictById
            else:
                rD = schemaDataDictById
                logger.warning("Unsupported style type %s" % styleType)
        except Exception as e:
            logger.exception("Failing with %s" % str(e))
            rD = schemaDataDictById

        return rD

    def __shapeRowwiseByName(self, schemaDataDictById):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            schemaObjName = self.__sD.getSchemaName(schemaId)
            iRowDList = schemaDataDictById[schemaId]
            oRowDList = []
            for iRowD in iRowDList:
                oRowD = {}
                for atId in iRowD:
                    oRowD[schemaObj.getAttributeName(atId)] = iRowD[atId]
                oRowDList.append(oRowD)
            rD[schemaObjName] = oRowDList
        return rD

    def __shapeRowwiseByNameWithCard(self, schemaDataDictById):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            schemaObjName = self.__sD.getSchemaName(schemaId)
            unitCard = self.__sD.hasUnitCardinality(schemaId)
            iRowDList = schemaDataDictById[schemaId]
            #
            if unitCard and len(iRowDList) == 1:
                iRowD = iRowDList[0]
                oRowD = {}
                for atId in iRowD:
                    oRowD[schemaObj.getAttributeName(atId)] = iRowD[atId]
                rD[schemaObjName] = oRowD
            else:
                oRowDList = []
                for iRowD in iRowDList:
                    oRowD = {}
                    for atId in iRowD:
                        oRowD[schemaObj.getAttributeName(atId)] = iRowD[atId]
                    oRowDList.append(oRowD)
                rD[schemaObjName] = oRowDList
        return rD

    def __shapeColumnwise(self, schemaDataDictById):
        rD = {}
        for schemaId in schemaDataDictById:
            schemaObj = self.__sD.getSchemaObject(schemaId)
            schemaObjName = self.__sD.getSchemaName(schemaId)
            iRowDList = schemaDataDictById[schemaId]
            colD = {}
            for iRowD in iRowDList:
                for atId in iRowD:
                    atName = schemaObj.getAttributeName(atId)
                    if atName not in colD:
                        colD[atName] = []
                    colD[atName].append(iRowD[atId])
            rD[schemaObjName] = colD
        return rD

    def __shapeRowwiseNoName(self, schemaDataDictById):
        rD = {}
        for schemaId in schemaDataDictById:
            # schemaObj = self.__sD.getSchemaObject(schemaId)
            schemaObjName = self.__sD.getSchemaName(schemaId)
            atIdList = self.__sD.getAttributeIdList(schemaId)
            atNameList = self.__sD.getAttributeNameList(schemaId)
            #
            iRowDList = schemaDataDictById[schemaId]
            oRowList = []
            for iRowD in iRowDList:
                oRowL = []
                for atId in atIdList:
                    oRowL.append(iRowD[atId])
                oRowList.append(oRowL)
            #
            rD[schemaObjName] = {'attributes': atNameList, 'data': oRowList}
        return rD

    # ---------------------- ---------------------- ---------------------- ---------------------- ----------------------
    #
    def __sliceRowwiseByNameWithCardOnePass(self, schemaDataDictById, sliceFilter, sliceIndex):

        #
        schemaIdExtraL = self.__sD.getSliceExtraSchemaIds(sliceFilter)
        #logger.info("Schema Id extras %r" % schemaIdExtraL)
        #
        for schemaId in schemaDataDictById:
            # sliceIndex = {'schemaId0': {(pCat0,pAt0): chAt0,  (pCat1,pAt1): chAt1}, ... }, ... }
            if schemaId in sliceIndex:
                logger.debug("SLICE %s - schemaId %s -> %r" % (sliceFilter, schemaId, sliceIndex[schemaId]))
        #
        # Build  value -> parent attributes dictionary -
        #
        sliceValues = SliceValues(schemaDataDictById, self.__sD, sliceFilter)
        pvD = {}
        pVals = []
        for pvTupL in sliceValues:
            vL = []
            pL = []
            for pvTup in pvTupL:
                pL.append(pvTup[0])
                vL.append(pvTup[1])
                pVals.append(pvTup[1])
            pvD[tuple(vL)] = tuple(pL)

        retD = {k: {} for k in pVals}
        # Each slice value has the form: (pCat0,pAt0), v0), (pCat1,pAt1), v1),...)
        #
        # Get the dictionary schemaId -> (chAt, chAt) where chAtn are in parent value order -
        #
        sfAtD = {}
        singleKeyAtD = {}
        sliceValues = SliceValues(schemaDataDictById, self.__sD, sliceFilter)
        pvTupL = next(sliceValues)
        #
        # Each parent key in the slice filter -
        ##
        for pvTup in pvTupL:
            logger.debug("VALUES > Slice filter %s parent %r value %r" % (sliceFilter, pvTup[0], pvTup[1]))
            # sliceIndex = {'schemaId0': mD, ... }
            #         mD = {(pCat0,pAt0): chAt0,  (pCat1,pAt1): chAt1}, ... }, ... }
            for schemaId, mD in sliceIndex.items():
                sfAtD[schemaId] = {}
                if schemaId in schemaDataDictById and pvTup[0] in mD:
                    sfAtD[schemaId].setdefault(pvTup[0], []).extend([k for k in mD[pvTup[0]]])
                    singleKeyAtD.setdefault(schemaId, []).extend([k for k in mD[pvTup[0]]])
                if len(sfAtD[schemaId]) > 1:
                    logger.error("Unsupported slice complexity %s key length %d" % (sliceFilter, len(sfAtD[schemaId])))
        logger.debug("Ordered slice filter attribute dictionary %r" % singleKeyAtD)
        #
        # Slice extra objects get replicated in each slice -
        #
        if schemaIdExtraL:
            rD = {}
            for schemaId in schemaIdExtraL:
                schemaObj = self.__sD.getSchemaObject(schemaId)
                schemaObjName = self.__sD.getSchemaName(schemaId)
                iRowDList = schemaDataDictById[schemaId]
                #
                oRowDList = []
                for iRowD in iRowDList:
                    oRowD = {}
                    for atId in iRowD:
                        oRowD[schemaObj.getAttributeName(atId)] = iRowD[atId]
                    oRowDList.append(oRowD)

                if (len(oRowDList) < 1) and not schemaObj.isMandatory():
                    logger.debug("Schema id %r row length %r mandatory %r" % (schemaId, len(oRowDList), schemaObj.isMandatory()))
                    continue

                if schemaObj.hasSliceUnitCardinality(sliceFilter) and len(oRowDList) == 1:
                    rD[schemaObjName] = oRowDList[0]
                else:
                    rD[schemaObjName] = oRowDList
            for pv in pVals:
                retD[pv] = copy.copy(rD)
        #
        #logger.info("slice %s retD keys after slice extra insertion %r" % (sliceFilter, list(retD.keys())))
        # logger.info("slice %s retD after slice extra insertion %r" % (sliceFilter, retD))

        #
        # Split of the rest by slice value - for single parent key slices  -
        #
        #logger.info("slice %s singleKeyAtD.keys() %r" % (sliceFilter, list(singleKeyAtD.keys())))
        #
        for schemaId, atL in singleKeyAtD.items():
            #
            schemaObj = self.__sD.getSchemaObject(schemaId)
            # ------
            schemaObjName = self.__sD.getSchemaName(schemaId)
            #
            uFlag = schemaObj.hasSliceUnitCardinality(sliceFilter)
            #
            iRowDList = schemaDataDictById[schemaId]
            rvS = set()
            for iRowD in iRowDList:
                oRowD = {schemaObj.getAttributeName(atId): iRowD[atId] for atId in iRowD}
                #
                rvS = set([iRowD[at] if at in iRowD else None for at in atL])
                for rv in rvS:
                    #logger.info("Slice %s schemaId %s uFlag %r value %r ADD ROW %r" % (sliceFilter, schemaObjName, uFlag, rv, oRowD))
                    if rv:
                        #
                        if uFlag:
                            retD[rv][schemaObjName] = oRowD
                        else:
                            retD[rv].setdefault(schemaObjName, []).append(oRowD)
            #
            #logger.info("Slice %s Finished loading schema name %s values %r" % (sliceFilter, schemaObjName, rvS))
            #
            #
            if False:
                for pv in retD:
                    if schemaObjName in retD[pv]:
                        logger.info(">>>>>>>>")
                        logger.info("slice %s schemaObjName %s value %r obj %r" % (sliceFilter, schemaObjName, pv, retD[pv][schemaObjName]))
                        logger.info(">>>>>>>>")
        #
        return list(retD.values())
