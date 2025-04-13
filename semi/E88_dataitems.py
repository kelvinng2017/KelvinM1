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


class ACTIVETRANSFERSUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ACTIVEZONESUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class CARRIERID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


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


class CARRIERSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-------------------------------------+
        | Value | Description    | Constant                            |
        +=======+================+=====================================+
        | 1     | WAIT_IN        | :const:`CARRIERSTATE.WAIT_IN`       |
        +-------+------------------------+-----------------------------+
        | 2     | TRANSFERRING   | :const:`CARRIERSTATE.TRANSFERRING`  |
        +-------+----------------+-------------------------------------+
        | 3     | WAIT_OUT       | :const:`CARRIERSTATE.WAIT_OUT`      |
        +-------+----------------+-------------------------------------+
        | 4     | COMPLETED      | :const:`CARRIERSTATE.COMPLETED`     |
        +-------+----------------+-------------------------------------+
        | 5     | ALTERNATE      | :const:`CARRIERSTATE.ALTERNATE`     |
        +-------+----------------+-------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    WAIT_IN=1
    TRANSFERRING=2
    WAIT_OUT=3
    COMPLETED=4
    ALTERNATE=5


class CARRIERSTATUS(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarBoolean


class CARRIERZONENAME(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class COMMANDNAME(DataItemBase):
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
    __count__=64


class COMMANDINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class COMMANDTYPE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class DEST(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class EMPTYCARRIER(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+--------------------------------+
        | Value | Description    | Constant                       |
        +=======+================+================================+
        | 0     | EMPTY          | :const:`EMPTYCARRIER.EMPTY`    |
        +-------+----------------+--------------------------------+
        | 1     | NOT EMPTY      | :const:`EMPTYCARRIER.NONEMPTY` |
        +-------+----------------+--------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    EMPTY=0
    NONEMPTY=1


class ENHANCEDCARRIERSUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDPORTSUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDTRANSFERSUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ENHANCEDACTIVEZONESUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ERRORID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class HANDOFFTYPE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+--------------------------------+
        | Value | Description    | Constant                       |
        +=======+================+================================+
        | 1     | MANUAL         | :const:`HANDOFFTYPE.MANUAL`    |
        +-------+----------------+--------------------------------+
        | 2     | AUTO           | :const:`HANDOFFTYPE.AUTO`      |
        +-------+----------------+--------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    MANUAL=1
    AUTO=2


class IDREADSTATUS(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+----------------------------------+
        | Value | Description    | Constant                         |
        +=======+================+==================================+
        | 0     | SUCCESS        | :const:`IDREADSTATUS.SUCC`       |
        +-------+----------------+----------------------------------+
        | 1     | FAILURE        | :const:`IDREADSTATUS.FAIL`       |
        +-------+----------------+----------------------------------+
        | 2     | DUPLICATE      | :const:`IDREADSTATUS.DUPLICATE`  |
        +-------+----------------+----------------------------------+
        | 3     | MISMATCH       | :const:`IDREADSTATUS.MISMATCH`   |
        +-------+----------------+----------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    SUCC=0
    FAIL=1
    DUPLICATE=2
    MISMATCH=3


class INSTALLTIME(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=16


class PORTID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class PORTIOTYPE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU1 <secsgem.secs.variables.SecsVarU1>`

    **Values**
        +-------+----------------+--------------------------------------+
        | Value | Description    | Constant                             |
        +=======+================+======================================+
        | 1     | loader         | :const:`PORTIOTYPE.LOADER`           |
        +-------+----------------+--------------------------------------+
        | 2     | unloader       | :const:`PORTIOTYPE.UNLOADER`         |
        +-------+----------------+--------------------------------------+
        | 3     | mixed          | :const:`PORTIOTYPE.MIXED`            |
        +-------+----------------+--------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU1

    LOADER=1
    UNLOADER=2
    MIXED=3


class PORTSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+--------------------------------------+
        | Value | Description    | Constant                             |
        +=======+================+======================================+
        | 1     | OutOfService   | :const:`PORTSTATE.OUTOFSERVICE`      |
        +-------+----------------+--------------------------------------+
        | 2     | InService      | :const:`PORTSTATE.INSERVICE`         |
        +-------+----------------+--------------------------------------+
        | 3     | TransferBlock  | :const:`PORTSTATE.TRANSFERBLOCK`     |
        +-------+----------------+--------------------------------------+
        | 4     | ReadyToLoad    | :const:`PORTSTATE.READYTOLOAD`       |
        +-------+----------------+--------------------------------------+
        | 5     | ReadyToUnload  | :const:`PORTSTATE.READYTOUNLOAD`     |
        +-------+----------------+--------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    OUTOFSERVICE=1
    INSERVICE=2
    TRANSFERBLOCK=3
    READYTOLOAD=4
    READYTOUNLOAD=5


class PORTTYPE(DataItemBase): 
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64 # max length


class POS(DataItemBase):
    """Equipment model type 

    :Types:
       - :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS01F02 <secsgem.secs.functions.SecsS01F02>`
        - :class:`SecsS01F13 <secsgem.secs.functions.SecsS01F13>`
        - :class:`SecsS01F14 <secsgem.secs.functions.SecsS01F14>`
        - :class:`SecsS07F22 <secsgem.secs.functions.SecsS07F22>`
        - :class:`SecsS07F23 <secsgem.secs.functions.SecsS07F23>`
        - :class:`SecsS07F26 <secsgem.secs.functions.SecsS07F26>`
        - :class:`SecsS07F31 <secsgem.secs.functions.SecsS07F31>`
        - :class:`SecsS07F39 <secsgem.secs.functions.SecsS07F39>`
        - :class:`SecsS07F43 <secsgem.secs.functions.SecsS07F43>`

    """

    __type__=SecsVarString
    __count__=20


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


class RECOVEROPTIONS(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class RESULTCODE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-----------------------------+
        | Value | Description    | Constant                    |
        +=======+================+=============================+
        | 0     | SUCCESS        | :const:`RESULTCODE.SUCC`    |
        +-------+----------------+-----------------------------+
        | 1     | CANCELED       | :const:`RESULTCODE.CANCEL`  |
        +-------+----------------+-----------------------------+
        | 2     | ABORTED        | :const:`RESULTCODE.ABORT`   |
        +-------+----------------+-----------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    SUCC=0
    CANCEL=1
    ABORT=2


class SCSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-----------------------------+
        | Value | Description    | Constant                    |
        +=======+================+=============================+
        | 1     | SC INIT        | :const:`SCSTATE.INIT`       |
        +-------+------------------------+---------------------+
        | 2     | PAUSED         | :const:`SCSTATE.PAUSED`     |
        +-------+----------------+-----------------------------+
        | 3     | AUTO           | :const:`SCSTATE.AUTO`       |
        +-------+----------------+-----------------------------+
        | 4     | PAUSING        | :const:`SCSTATE.PAUSING`    |
        +-------+----------------+-----------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    INIT=1
    PAUSED=2
    AUTO=3
    PAUSING=4


class SLOTACK(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SLOTDATA(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SLOTID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SLOTMSG(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SLOTPRESERVED(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SLOTSTATUS(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class SOURCE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class STOCKERCRANEID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class STOCKERUNITID(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class STOCKERUNITINFO(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class STOCKERUNIT(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarArray>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarArray]


class STOCKERUNITSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-----------------------------+
        | Value | Description    | Constant                    |
        +=======+================+=============================+
        | 0     | SUCCESS        | :const:`RESULTCODE.SUCC`    |
        +-------+----------------+-----------------------------+
        | 1     | CANCELED       | :const:`RESULTCODE.CANCEL`  |
        +-------+----------------+-----------------------------+
        | 2     | ABORTED        | :const:`RESULTCODE.ABORT`   |
        +-------+----------------+-----------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    SUCC=0
    CANCEL=1
    ABORT=2


class TRANSFERCOMMAND(DataItemBase):
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


class TRANSFERSTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+--------------------------------------+
        | Value | Description    | Constant                             |
        +=======+================+======================================+
        | 1     | QUEUED         | :const:`TRANSFERSTATE.QUEUED`        |
        +-------+------------------------+------------------------------+
        | 2     | TRANSFERRING   | :const:`TRANSFERSTATE.TRANSFERRING`  |
        +-------+----------------+--------------------------------------+
        | 3     | PAUSED         | :const:`TRANSFERSTATE.PAUSED`        |
        +-------+----------------+--------------------------------------+
        | 4     | CANCELING      | :const:`TRANSFERSTATE.CANCELING`     |
        +-------+----------------+--------------------------------------+
        | 5     | ABORTING       | :const:`TRANSFERSTATE.ABORTING`      |
        +-------+----------------+--------------------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    QUEUED=1
    TRANSFERRING=2
    PAUSED=3
    CANCELING=4
    ABORTING=5


class ZONECAPACITY(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2


class ZONEDATA(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarList <secsgem.secs.variables.SecsVarList>`
       :Length: 1

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarDynamic
    __allowedtypes__=[SecsVarList]


class ZONENAME(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarString <secsgem.secs.variables.SecsVarString>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarString
    __count__=64


class ZONESIZE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2


class ZONESTATE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+----------------+-----------------------------+
        | Value | Description    | Constant                    |
        +=======+================+=============================+
        | 0     | OTHER          | :const:`SCSTATE.OTHER`      |
        +-------+------------------------+---------------------+
        | 1     | UP             | :const:`SCSTATE.UP`         |
        +-------+----------------+-----------------------------+
        | 2     | DOWN           | :const:`SCSTATE.DOWN`       |
        +-------+----------------+-----------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    UP=0
    DOWN=1
    OTHER=2


class ZONETYPE(DataItemBase):
    """Enhance Command parameter acknowledge code

       :Types: :class:`SecsVarU2 <secsgem.secs.variables.SecsVarU2>`

    **Values**
        +-------+---------------+---------------------------+
        | Value | Description   | Constant                  |
        +=======+===============+===========================+
        | 1     | SHELF         | :const:`ZONETYPE.SHELF`   |
        +-------+------------------------+------------------+
        | 2     | PORT          | :const:`ZONETYPE.PORT`    |
        +-------+---------------+---------------------------+
        | 3     | OTHER         | :const:`ZONETYPE.OTHER`   |
        +-------+---------------+---------------------------+

    **Used In Function**
        - :class:`SecsS02F50 <secsgem.secs.functions.SecsS02F50>`
    """

    __type__=SecsVarU2

    SHELF=1
    PORT=2
    OTHER=3

