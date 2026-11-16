"""Pure recommendation math: feature vectors, taste profiles, ranking and offline eval.

No FastAPI, SQLAlchemy or provider imports. Services pass plain arrays/DataFrames in
and get scores and explanations out.
"""
from app.ml.eval import coverage, diversity, precision_at_k, recall_at_k
from app.ml.features import AUDIO_FEATURE_NAMES, FeatureMatrix, build_feature_matrix
from app.ml.rank import Explanation, RankedItem, mmr_select, rank_by_cosine, similar_to_seed
from app.ml.scorer import FEATURE_NAMES, MIN_LABELED_SAMPLES, build_song_features, train_logistic
from app.ml.taste import Signal, TasteProfile, blend_profiles, build_taste_profile

__all__ = [
    "AUDIO_FEATURE_NAMES",
    "FEATURE_NAMES",
    "MIN_LABELED_SAMPLES",
    "Explanation",
    "FeatureMatrix",
    "RankedItem",
    "Signal",
    "TasteProfile",
    "blend_profiles",
    "build_feature_matrix",
    "build_song_features",
    "build_taste_profile",
    "coverage",
    "diversity",
    "mmr_select",
    "precision_at_k",
    "rank_by_cosine",
    "recall_at_k",
    "similar_to_seed",
    "train_logistic",
]
