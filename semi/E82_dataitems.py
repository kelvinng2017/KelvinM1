from secsgem import*
from secsgem.secs import *

class ACTIVECARRIERSUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic # type
    __allowedtypes__=[SecsVarList] # allowed type
    
class ENHANCEDCARRIERUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic # type
    __allowedtypes__=[SecsVarList] # allowed type


class ACTIVERACKUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ACTIVETRANSFERSUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ACTIVEVEHICLESUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ASSOCIATEDATA(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class CARRIERID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=300 # max length


class CARRIERIDLISTUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class CARRIERINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList] # allowed type


class CARRIERLOC(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class COMMANDID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=100


class COMMANDINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class CURRENTPORTSTATEUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class DESTPORT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class ENHANCEDCARRIERINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDCARRIERINFOUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDTRANSFERCOMMAND(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDTRANSFERCOMMANDUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDVEHICLEINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDVEHICLEINFOUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class EQLIST(DataItemBase): # Mike: 2020/11/11
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class LOTID(DataItemBase): # Mike: 2020/11/11
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class INSTALLTIME(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=16


class MACHINE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class NEXTSTEP(DataItemBase): # Mike: 2020/11/11
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class PORTID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class PORTINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class PORTTRANSFERSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+-----------------+---------------------------------------------+
        | Value | Description     | Constant                                    |
        +=======+=================+=============================================+
        | 1     | OUT OF SERVICE  | :const:`PORTTRANSFERSTATE.OUT_OF_SERVICE`   |
        +-------+-----------------+---------------------------------------------+
        | 2     | IN SERVICE      | :const:`PORTTRANSFERSTATE.IN_SERVICE`       |
        +-------+-----------------+---------------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    # pre-defined value
    OUT_OF_SERVICE=1
    IN_SERVICE=2


class PRIORITY(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+--------------------+--------------------------------+
        | Value | Description        | Constant                       |
        +=======+====================+================================+
        | 0     | INVALID            | :const:`PRIORITY.INVALID`      |
        +-------+--------------------+--------------------------------+
        | 1-99  | priority low-high  |                                |
        +-------+--------------------+--------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    INVALID=0


class RACKID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class RACKLOCATION(DataItemBase): # Mike: 2021/05/11
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class RACKSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarArray]


class RACKSTATEUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class REPLACE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+--------------------------+
        | Value | Description    | Constant                 |
        +=======+================+==========================+
        | 0     | OFF            | :const:`COMMANDID.OFF`   |
        +-------+----------------+--------------------------+
        | >1    | ON             |                          |
        +-------+----------------+--------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    OFF=0


class SLOTID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SOURCEPORT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class STATUS(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class TRANSFERCOMMAND(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class TRANSFERCOMMANDUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarArray]


class TRANSFERCOMPLETEINFOUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class TRANSFERINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class TRANSFERINFOUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class TRANSFERINFOLISTUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class TRANSFERPORT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class TRANSFERPORTLIST(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarArray]


class TRANSFERSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-------------------------------------+
        | Value | Description    | Constant                            |
        +=======+================+=====================================+
        | 1     | QUEUED         | :const:`VEHICLESTATE.QUEUED`        |
        +-------+------------------------+-----------------------------+
        | 2     | TRANSFERRING   | :const:`VEHICLESTATE.TRANSFERRING`  |
        +-------+----------------+-------------------------------------+
        | 3     | PAUSED         | :const:`VEHICLESTATE.PAUSED`        |
        +-------+----------------+-------------------------------------+
        | 4     | CANCELING      | :const:`VEHICLESTATE.CANCELING`     |
        +-------+----------------+-------------------------------------+
        | 5     | ABORTING       | :const:`VEHICLESTATE.ABORTING`      |
        +-------+----------------+-------------------------------------+
        | 6     | WAITING        | :const:`VEHICLESTATE.WAITING`       |
        +-------+----------------+-------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    QUEUED=1
    TRANSFERRING=2
    PAUSED=3
    CANCELING=4
    ABORTING=5
    WAITING=6


class VEHICLEID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`
       :Length: 120

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class VEHICLEINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]
    
class UNITINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]

class ALID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`
       :Length: 120

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64
    
class ALARMTEXT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`
       :Length: 120

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64

class VEHICLELOCATION(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class VEHICLESTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-------------------------------------+
        | Value | Description    | Constant                            |
        +=======+================+=====================================+
        | 1     | REMOVE         | :const:`VEHICLESTATE.REMOVE`        |
        +-------+------------------------+-----------------------------+
        | 2     | NOT ASSIGNED   | :const:`VEHICLESTATE.NOT_ASSIGNED`  |
        +-------+----------------+-------------------------------------+
        | 3     | ENROUTE        | :const:`VEHICLESTATE.ENROUTE`       |
        +-------+----------------+-------------------------------------+
        | 4     | PARKED         | :const:`VEHICLESTATE.PARKED`        |
        +-------+----------------+-------------------------------------+
        | 5     | ACQUIRING      | :const:`VEHICLESTATE.ACQUIRING`     |
        +-------+----------------+-------------------------------------+
        | 6     | DEPOSITING     | :const:`VEHICLESTATE.DEPOSITING`    |
        +-------+----------------+-------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    REMOVE=1
    NOT_ASSIGNED=2
    ENROUTE=3
    PARKED=4
    ACQUIRING=5
    DEPOSITING=6


class VEHICLESOH(DataItemBase): # Mike: 2021/05/14
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarU2>`
       :Length: 120

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2
    
class CARRIERSTATE(DataItemBase): # Mike: 2021/05/14
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-------------------------------------+
        | Value | Description    | Constant                            |
        +=======+================+=====================================+
        | 1     | WAIT IN        | :const:`VEHICLESTATE.WAIT_IN `      |
        +-------+------------------------+-----------------------------+
        | 2     | TRANSFERING    | :const:`VEHICLESTATE.TRANSFERING`   |
        +-------+----------------+-------------------------------------+
        | 3     | COMPLETE       | :const:`VEHICLESTATE.COMPLETE`      |
        +-------+----------------+-------------------------------------+
        | 4     | ALTERNATE      | :const:`VEHICLESTATE.ALTERNATE`     |
        +-------+----------------+-------------------------------------+
        | 5     | WAIT OUT       | :const:`VEHICLESTATE.WAIT_OUT`      |
        +-------+----------------+-------------------------------------+
        | 6     | INSTALLED      | :const:`VEHICLESTATE.INSTALLED`     |
        +-------+----------------+-------------------------------------+

    **Used In Function**
        - :class:`SecsS01F03 <secsgem.secs.functions.SecsS01F03>`
        
        for Mirle MCS only have INSTALLED=6
    """

    __type__=SecsVarU2

    WAIT_IN=1
    TRANSFERING=2
    COMPLETE=3
    ALTERNATE=4
    WAIT_OUT=5
    INSTALLED=6
    
class INSTALLTIME(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64
