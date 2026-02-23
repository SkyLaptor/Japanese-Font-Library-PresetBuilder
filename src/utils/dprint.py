DEBUG_PREFIX = "[DEBUG]: "


def dprint(msg: str, debug: bool = False, prefix: str = DEBUG_PREFIX):
    """
    デバッグモードが有効の時にメッセージを表示する

    :param msg: メッセージ
    :type msg: str
    :param debug: デバッグモード
    :type debug: bool
    :param prefix: 接詞詞
    :type prefix: str
    """
    if debug:
        print(f"{prefix}{msg}")
