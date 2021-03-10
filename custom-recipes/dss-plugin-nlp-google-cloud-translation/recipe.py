# -*- coding: utf-8 -*-
from typing import Dict, AnyStr
from ratelimit import limits, RateLimitException
from retry import retry

import dataiku
from dataiku.customrecipe import get_recipe_config, get_input_names_for_role, get_output_names_for_role

import json
from google_translate_api_client import API_EXCEPTIONS, get_client
from plugin_io_utils import ErrorHandlingEnum, validate_column_input
from dku_io_utils import set_column_description
from api_parallelizer import api_parallelizer
from google_translate_api_formatting import TranslationAPIFormatter


# ==============================================================================
# SETUP
# ==============================================================================

api_configuration_preset = get_recipe_config().get("api_configuration_preset")
if api_configuration_preset is None or api_configuration_preset == {}:
    raise ValueError("Please specify an API configuration preset")

# Recipe parameters
text_column = get_recipe_config().get("text_column")
target_language = get_recipe_config().get("target_language", "")
source_language = get_recipe_config().get("source_language", "").replace("auto", "")

# Params for parallelization
column_prefix = "translation_api"
parallel_workers = api_configuration_preset.get("parallel_workers")
error_handling = ErrorHandlingEnum[get_recipe_config().get("error_handling")]

# Params for translation
client = get_client(api_configuration_preset.get("gcp_service_account_key"))
api_quota_rate_limit = api_configuration_preset.get("api_quota_rate_limit")
api_quota_period = api_configuration_preset.get("api_quota_period")

# ==============================================================================
# DEFINITIONS
# ==============================================================================

input_dataset = dataiku.Dataset(get_input_names_for_role("input_dataset")[0])
output_dataset = dataiku.Dataset(get_output_names_for_role("output_dataset")[0])
validate_column_input(text_column, [col["name"] for col in input_dataset.read_schema()])
input_df = input_dataset.get_dataframe()

@retry((RateLimitException, OSError), delay=api_quota_period, tries=5)
@limits(calls=api_quota_rate_limit, period=api_quota_period)
def call_translation_api(row: Dict, text_column: AnyStr, target_language: AnyStr, source_language: AnyStr =None) -> AnyStr:
    text = row[text_column]
    if not isinstance(text, str) or str(text).strip() == "":
        return json.dumps({})
    else:
        response = client.translate(text, target_language, source_language=source_language)
        return json.dumps(response)

formatter = TranslationAPIFormatter(
    input_df=input_df, input_column=text_column, target_language=target_language, source_language=source_language, column_prefix=column_prefix, error_handling=error_handling
)

# ==============================================================================
# RUN
# ==============================================================================

df = api_parallelizer(
    input_df=input_df,
    api_call_function=call_translation_api,
    api_exceptions=API_EXCEPTIONS,
    column_prefix=column_prefix,
    parallel_workers=parallel_workers,
    error_handling=error_handling,
    text_column=text_column,
    target_language=target_language,
)
output_df = formatter.format_df(df)
output_dataset.write_with_schema(output_df)

set_column_description(
    input_dataset=input_dataset,
    output_dataset=output_dataset,
    column_description_dict=formatter.column_description_dict,
)
