class ConfigConverterBase:
    """
    通用設定檔轉換器的基礎類別 (Base Interface for Configuration Converters)。
    每個特定的模擬器都需要實作此介面來將統一的 YAML 轉換為自己專屬的格式。
    """
    def __init__(self, master_config):
        self.config = master_config

    def convert(self, output_filepath):
        """
        執行轉換並將結果寫入至 output_filepath。
        由子類別實作。
        """
        raise NotImplementedError("Subclasses must implement convert()")
