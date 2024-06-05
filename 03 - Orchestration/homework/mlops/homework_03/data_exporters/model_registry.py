import os
from typing import Dict, Optional, Tuple, Union

import mlflow
import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from mlflow.tracking import MlflowClient
#from mlflow import MlflowClient
from mlflow.data import from_numpy, from_pandas
from mlflow.entities import DatasetInput, InputTag, Run
from mlflow.models import infer_signature, signature
from mlflow.sklearn import log_model as log_model_sklearn
from mlflow.xgboost import log_model as log_model_xgboost
from sklearn.base import BaseEstimator

# Ensure the data_exporter decorator is correctly defined and imported
if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

DEFAULT_DEVELOPER = os.getenv('EXPERIMENTS_DEVELOPER', 'chuks')
DEFAULT_EXPERIMENT_NAME = 'nyc-taxi-experiment'
#DEFAULT_TRACKING_URI = 'sqlite:///mlflow.db'


TRACKING_SERVER_HOST = "0.0.0.0"
mlflow.set_tracking_uri(f"http://{TRACKING_SERVER_HOST}:5001")
print(f"MLflow version: {mlflow.__version__}")
print(f"tracking URI: '{mlflow.get_tracking_uri()}'")

@data_exporter
def setup_experiment(
    experiment_name: Optional[str] = None,
    tracking_uri: Optional[str] = None,
) -> Tuple[MlflowClient, str]:
    mlflow.set_tracking_uri(tracking_uri or DEFAULT_TRACKING_URI)
    experiment_name = experiment_name or DEFAULT_EXPERIMENT_NAME

    #client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)

    if experiment:
        experiment_id = experiment.experiment_id
    else:
        experiment_id = client.create_experiment(experiment_name)

    print(f"tracking URI: '{mlflow.get_tracking_uri()}'")

    return client, experiment_id

def track_experiment(
    experiment_name: Optional[str] = None,
    block_uuid: Optional[str] = None,
    developer: Optional[str] = None,
    hyperparameters: Dict[str, Union[float, int, str]] = {},
    metrics: Dict[str, float] = {},
    model: Optional[BaseEstimator] = None,
    partition: Optional[str] = None,
    pipeline_uuid: Optional[str] = None,
    predictions: Optional[np.ndarray] = None,
    run_name: Optional[str] = None,
    tracking_uri: Optional[str] = None,
    training_set: Optional[pd.DataFrame] = None,
    training_targets: Optional[pd.Series] = None,
    track_datasets: bool = False,
    validation_set: Optional[pd.DataFrame] = None,
    validation_targets: Optional[pd.Series] = None,
    verbosity: Union[bool, int] = False,  # False by default or else it creates too many logs
    **kwargs,
) -> mlflow.entities.Run:
    experiment_name = experiment_name or DEFAULT_EXPERIMENT_NAME
    tracking_uri = tracking_uri or DEFAULT_TRACKING_URI

    client, experiment_id = setup_experiment(experiment_name, tracking_uri)

    if not run_name:
        run_name = ':'.join(
            [str(s) for s in [pipeline_uuid, partition, block_uuid] if s]
        )

    run = client.create_run(experiment_id, run_name=run_name or None)
    run_id = run.info.run_id

    for key, value in [
        ('developer', developer or DEFAULT_DEVELOPER),
        ('model', model.__class__.__name__),
    ]:
        if value is not None:
            client.set_tag(run_id, key, value)

    for key, value in [
        ('block_uuid', block_uuid),
        ('partition', partition),
        ('pipeline_uuid', pipeline_uuid),
    ]:
        if value is not None:
            client.log_param(run_id, key, value)

    for key, value in hyperparameters.items():
        client.log_param(run_id, key, value)
        if verbosity:
            print(f'Logged hyperparameter {key}: {value}.')

    for key, value in metrics.items():
        client.log_metric(run_id, key, value)
        if verbosity:
            print(f'Logged metric {key}: {value}.')

    if model:
        log_model = None

        if isinstance(model, BaseEstimator):
            log_model = log_model_sklearn
        elif isinstance(model, xgb.Booster):
            log_model = log_model_xgboost

        if log_model:
            opts = dict(artifact_path='models', input_example=None)

            if training_set is not None and predictions is not None:
                opts['signature'] = infer_signature(training_set, predictions)

            log_model(model, **opts)
            if verbosity:
                print(f'Logged model {model.__class__.__name__}.')

    return run