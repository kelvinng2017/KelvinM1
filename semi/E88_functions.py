from secsgem.secs.dataitems import *
from .E88_dataitems import *


class SecsS01F02(SecsStreamFunction):
    """on line data

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
            POS: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
            <A "RTRRUFTRR0">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=1
    _function=2

    _dataFormat=[
        MDLN,
        SOFTREV,
        POS
    ]

    _toHost=True
    _toEquipment=True

    _hasReply=False
    _isReplyRequired=False

    _isMultiBlock=False


class SecsS01F05(SecsStreamFunction):
    """on line data

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
            POS: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
            <A "RTRRUFTRR0">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=1
    _function=5

    _dataFormat=[
        SVID
    ]

    _toHost=False
    _toEquipment=True

    _hasReply=True
    _isReplyRequired=True

    _isMultiBlock=False


class SecsS01F06(SecsStreamFunction):
    """on line data

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
            POS: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
            <A "RTRRUFTRR0">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=1
    _function=6

    _dataFormat=[
        CARRIERID
    ]

    _toHost=True
    _toEquipment=False

    _hasReply=False
    _isReplyRequired=False

    _isMultiBlock=False


class SecsS18F21(SecsStreamFunction):
    """led display control request

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=18
    _function=21

    _dataFormat=[
        SLOTID,
        [
            SLOTDATA
        ]
    ]

    _toHost=False
    _toEquipment=True

    _hasReply=True
    _isReplyRequired=True

    _isMultiBlock=False


class SecsS18F22(SecsStreamFunction):
    """on line data

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=18
    _function=22

    _dataFormat=[
        SLOTID,
        SLOTACK
    ]

    _toHost=True
    _toEquipment=False

    _hasReply=False
    _isReplyRequired=False

    _isMultiBlock=False


class SecsS18F71(SecsStreamFunction):
    """move in event

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=18
    _function=71

    _dataFormat=[
        SLOTID,
        SLOTSTATUS,
        SLOTPRESERVED,
        [
            SLOTMSG
        ]
    ]

    _toHost=True
    _toEquipment=False

    _hasReply=False
    _isReplyRequired=False

    _isMultiBlock=False


class SecsS18F75(SecsStreamFunction):
    """move out event

    .. caution::

        This Stream/function has different structures depending on the source.
        If it is sent from the eqipment side it has the structure below, if it
        is sent from the host it is an empty list.
        Be sure to fill the array accordingly.

    **Structure E->H**::

        {
            MDLN: A[20]
            SOFTREV: A[20]
        }

    **Example**::

        >>> import secsgem
        >>> secsgem.SecsS01F02(['secsgem', '0.0.6']) # E->H
        S1F2
          <L [2]
            <A "secsgem">
            <A "0.0.6">
          > .
        >>> secsgem.SecsS01F02() #H->E
        S1F2
          <L> .

    :param value: parameters for this function (see example)
    :type value: list
    """

    _stream=18
    _function=75

    _dataFormat=[
        SLOTID,
        SLOTSTATUS,
        SLOTPRESERVED,
        [
            SLOTMSG
        ]
    ]

    _toHost=True
    _toEquipment=False

    _hasReply=False
    _isReplyRequired=False

    _isMultiBlock=False


Extend_secsStreamsFunctions={
    1: {
        2: SecsS01F02,
        5: SecsS01F05,
        6: SecsS01F06,
    },
    18: {
        21: SecsS18F21,
        22: SecsS18F22,
        71: SecsS18F71,
        75: SecsS18F75,
    },
}
