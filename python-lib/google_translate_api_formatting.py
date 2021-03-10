# -*- coding: utf-8 -*-
"""Module with classes to format results from the Google NLP API"""

import logging
import pandas as pd
import json
from enum import Enum
from typing import AnyStr, Dict, List, Union

from plugin_io_utils import (
    API_COLUMN_NAMES_DESCRIPTION_DICT,
    ErrorHandlingEnum,
    build_unique_column_names,
    generate_unique,
    safe_json_loads,
    move_api_columns_to_end,
)


# ==============================================================================
# CLASS AND FUNCTION DEFINITION
# ==============================================================================


class GenericAPIFormatter:
    """
    Geric Formatter class for API responses:
    - initialize with generic parameters
    - compute generic column descriptions
    - apply format_row to dataframe
    """

    def __init__(
        self,
        input_df: pd.DataFrame,
        column_prefix: AnyStr = "api",
        error_handling: ErrorHandlingEnum = ErrorHandlingEnum.LOG,
    ):
        self.input_df = input_df
        self.column_prefix = column_prefix
        self.error_handling = error_handling
        self.api_column_names = build_unique_column_names(input_df, column_prefix)
        self.column_description_dict = {
            v: API_COLUMN_NAMES_DESCRIPTION_DICT[k] for k, v in self.api_column_names._asdict().items()
        }

    def format_row(self, row: Dict) -> Dict:
        return row

    def format_df(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info("Formatting API results...")
        df = df.apply(func=self.format_row, axis=1)
        df = move_api_columns_to_end(df, self.api_column_names, self.error_handling)
        logging.info("Formatting API results: Done.")
        return df


class TranslationAPIFormatter(GenericAPIFormatter):
    """
    Formatter class for translation API responses:
    - make sure response is valid JSON
    """

    def __init__(
        self,
        input_df: pd.DataFrame,
        input_column: AnyStr,
        target_language: AnyStr,
        source_language: AnyStr = None,
        column_prefix: AnyStr = "translation_api",
        error_handling: ErrorHandlingEnum = ErrorHandlingEnum.LOG,
    ):
        super().__init__(input_df, column_prefix, error_handling)
        self.translated_text_column_name = generate_unique(
            "{input_column}_{language}".format(input_column=input_column, language=target_language.replace('-', '_')),
            input_df.columns, column_prefix)
        self.source_language = source_language
        self.input_column = input_column
        self._compute_column_description()

    def _compute_column_description(self):
        self.column_description_dict[self.translated_text_column_name] = \
            "{language} translation of the {col} column by the Google Translation API".format(
            language=self.source_language, col=self.input_column)

    def format_row(self, row: Dict) -> Dict:
        raw_response = row[self.api_column_names.response]
        response = safe_json_loads(raw_response, self.error_handling)
        if not self.source_language:
            row["detected_source_language"] = response.get('detectedSourceLanguage', None)
        row[self.translated_text_column_name] = response.get('translatedText', None)
        return row
