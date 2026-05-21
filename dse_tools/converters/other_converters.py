from .base_converter import ConfigConverterBase

class NoximConverter(ConfigConverterBase):
    def convert(self, output_filepath):
        # TODO: 實作轉換為 Noxim command line arguments 或 YAML
        pass

class PronocConverter(ConfigConverterBase):
    def convert(self, output_filepath):
        # TODO: 實作轉換為 ProNoC 需要的格式
        pass

class ConstellationConverter(ConfigConverterBase):
    def convert(self, output_filepath):
        # TODO: 實作轉換為 Constellation/Chisel 參數
        pass
