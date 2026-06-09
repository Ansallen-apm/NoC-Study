import sys
import os
from .base_converter import ConfigConverterBase

class NoximConverter(ConfigConverterBase):
    def convert(self, output_filepath):
        # TODO: 實作轉換為 Noxim command line arguments 或 YAML
        raise NotImplementedError("NoximConverter.convert() 尚未實作")

class PronocConverter(ConfigConverterBase):
    def convert(self, output_filepath):
        # TODO: 實作轉換為 ProNoC 需要的格式
        raise NotImplementedError("PronocConverter.convert() 尚未實作")

class ConstellationConverter(ConfigConverterBase):
    def convert(self, output_filepath):
        # TODO: 實作轉換為 Constellation/Chisel 參數
        raise NotImplementedError("ConstellationConverter.convert() 尚未實作")
