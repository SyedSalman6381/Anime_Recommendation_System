
"""
ANIVERSE Hybrid Recommendation Engine

The score combines:
- Genre overlap
- Theme/tag overlap
- TF-IDF similarity of title + synopsis + metadata
- Studio similarity
- Rating similarity
- Episode-count similarity
- Optional Jikan community recommendation votes
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


WEIGHTS = {
    "genre": 0.30,
    "tag": 0.20,
    "tfidf": 0.30,
    "studio": 0.05,
    "rating": 0.10,
    "episode": 0.05,
    "jikan": 0.10,
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).lower().strip()


def title_of(anime: Dict[str, Any]) -> str:
    title = anime.get("title") or {}
    if isinstance(title, str):
        return title or "Unknown Anime"
    return (
        title.get("english")
        or title.get("romaji")
        or title.get("native")
        or "Unknown Anime"
    )


def names_from_list(values: Any) -> List[str]:
    if not values:
        return []

    result = []
    for item in values:
        if isinstance(item, str):
            value = item
        elif isinstance(item, dict):
            value = item.get("name", "")
        else:
            value = ""

        value = clean_text(value)
        if value:
            result.append(value)

    return list(dict.fromkeys(result))


def genres_of(anime: Dict[str, Any]) -> List[str]:
    return names_from_list(anime.get("genres", []))


def tags_of(anime: Dict[str, Any]) -> List[str]:
    return names_from_list(anime.get("tags", []))


def studios_of(anime: Dict[str, Any]) -> List[str]:
    studios = anime.get("studios") or {}
    if isinstance(studios, dict):
        return names_from_list(studios.get("nodes", []))
    return names_from_list(studios)


def description_of(anime: Dict[str, Any]) -> str:
    return clean_text(anime.get("description", ""))


def overlap_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    a_set = set(a)
    b_set = set(b)

    if not a_set or not b_set:
        return 0.0

    return len(a_set & b_set) / max(1, min(len(a_set), len(b_set)))


def rating_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    try:
        a_score = float(a.get("averageScore", a.get("score", 0)) or 0)
        b_score = float(b.get("averageScore", b.get("score", 0)) or 0)
    except (TypeError, ValueError):
        return 0.0

    if a_score <= 0 or b_score <= 0:
        return 0.0

    return max(0.0, 1.0 - abs(a_score - b_score) / 50.0)


def episode_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    try:
        a_ep = float(a.get("episodes") or 0)
        b_ep = float(b.get("episodes") or 0)
    except (TypeError, ValueError):
        return 0.0

    if a_ep <= 0 or b_ep <= 0:
        return 0.0

    scale = max(a_ep, b_ep, 12.0)
    return max(0.0, 1.0 - abs(a_ep - b_ep) / scale)


def build_document(anime: Dict[str, Any]) -> str:
    title = clean_text(title_of(anime))
    description = description_of(anime)
    genres = genres_of(anime)
    tags = tags_of(anime)
    studios = studios_of(anime)

    # Repetition intentionally gives structured fields more influence.
    return " ".join(
        [
            title,
            title,
            description,
            description,
            " ".join(genres),
            " ".join(genres),
            " ".join(tags),
            " ".join(tags),
            " ".join(studios),
        ]
    )


def tfidf_scores(
    selected: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> List[float]:
    if not candidates:
        return []

    documents = [build_document(selected)] + [
        build_document(candidate) for candidate in candidates
    ]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=15000,
        )
        matrix = vectorizer.fit_transform(documents)
        return [
            float(x)
            for x in cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        ]
    except ValueError:
        return [0.0] * len(candidates)


def community_score(anime: Dict[str, Any]) -> float:
    try:
        votes = float(anime.get("recommendation_votes", 0) or 0)
    except (TypeError, ValueError):
        return 0.0

    return min(1.0, votes / 500.0)


def generate_reasons(
    selected: Dict[str, Any],
    candidate: Dict[str, Any],
    genre_score: float,
    tag_score: float,
    tfidf_score: float,
    studio_score: float,
    rating_score: float,
) -> List[str]:
    reasons: List[str] = []

    shared_genres = sorted(set(genres_of(selected)) & set(genres_of(candidate)))
    shared_tags = sorted(set(tags_of(selected)) & set(tags_of(candidate)))
    shared_studios = sorted(set(studios_of(selected)) & set(studios_of(candidate)))

    if shared_genres:
        reasons.append("Shared genres: " + ", ".join(shared_genres[:3]))

    if shared_tags:
        reasons.append("Similar themes: " + ", ".join(shared_tags[:3]))

    if shared_studios:
        reasons.append("Same studio: " + ", ".join(shared_studios[:2]))

    if tfidf_score >= 0.35:
        reasons.append("Similar story and keywords")

    if rating_score >= 0.80:
        reasons.append("Similar audience rating")

    if not reasons:
        reasons.append("Similar overall anime profile")

    return reasons[:3]


def remove_duplicates(
    candidates: List[Dict[str, Any]],
    selected_id: Any,
) -> List[Dict[str, Any]]:
    result = []
    seen = {selected_id}

    for anime in candidates:
        anime_id = anime.get("id")
        if anime_id in seen:
            continue

        if anime_id is not None:
            seen.add(anime_id)

        result.append(anime)

    return result


def apply_user_filters(
    candidates: List[Dict[str, Any]],
    preferred_genres: Optional[List[str]] = None,
    min_score: Optional[float] = None,
    max_episodes: Optional[int] = None,
) -> List[Dict[str, Any]]:
    preferred = {
        clean_text(x)
        for x in (preferred_genres or [])
        if clean_text(x)
    }

    result = []

    for anime in candidates:
        if min_score is not None:
            try:
                score = float(anime.get("averageScore", anime.get("score", 0)) or 0)
            except (TypeError, ValueError):
                score = 0

            if score < min_score:
                continue

        if max_episodes is not None:
            try:
                episodes = int(anime.get("episodes") or 0)
            except (TypeError, ValueError):
                episodes = 0

            if episodes and episodes > max_episodes:
                continue

        if preferred:
            if not set(genres_of(anime)) & preferred:
                continue

        result.append(anime)

    return result


def rank_candidates(
    selected: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    top_n: int = 10,
    preferred_genres: Optional[List[str]] = None,
    min_score: Optional[float] = None,
    max_episodes: Optional[int] = None,
) -> List[Dict[str, Any]]:
    candidates = remove_duplicates(candidates, selected.get("id"))
    candidates = apply_user_filters(
        candidates,
        preferred_genres=preferred_genres,
        min_score=min_score,
        max_episodes=max_episodes,
    )

    if not candidates:
        return []

    tfidf = tfidf_scores(selected, candidates)

    selected_genres = genres_of(selected)
    selected_tags = tags_of(selected)
    selected_studios = studios_of(selected)

    ranked = []

    for index, candidate in enumerate(candidates):
        genre_score = overlap_similarity(selected_genres, genres_of(candidate))
        tag_score = overlap_similarity(selected_tags, tags_of(candidate))
        text_score = tfidf[index] if index < len(tfidf) else 0.0
        studio_score = overlap_similarity(selected_studios, studios_of(candidate))
        rating_score = rating_similarity(selected, candidate)
        episode_score = episode_similarity(selected, candidate)
        community = community_score(candidate)

        has_community_signal = community > 0

        content_score = (
            WEIGHTS["genre"] * genre_score
            + WEIGHTS["tag"] * tag_score
            + WEIGHTS["tfidf"] * text_score
            + WEIGHTS["studio"] * studio_score
            + WEIGHTS["rating"] * rating_score
            + WEIGHTS["episode"] * episode_score
        )

        if has_community_signal:
            final_score = content_score + WEIGHTS.get("jikan", 0.0) * community
            denominator = sum(WEIGHTS.values())
            if denominator:
                final_score /= denominator
        else:
            # No community signal: normalize only by content weights.
            content_weight = sum(WEIGHTS.values())
            final_score = content_score / content_weight if content_weight else 0.0

        try:
            average_score = float(
                candidate.get("averageScore", candidate.get("score", 0)) or 0
            )
        except (TypeError, ValueError):
            average_score = 0

        if average_score >= 85:
            final_score += 0.02

        final_score = max(0.0, min(1.0, final_score))

        ranked.append(
            {
                "anime": candidate,
                "score": final_score,
                "reasons": generate_reasons(
                    selected,
                    candidate,
                    genre_score,
                    tag_score,
                    text_score,
                    studio_score,
                    rating_score,
                ),
                "signals": {
                    "genre": genre_score,
                    "tag": tag_score,
                    "tfidf": text_score,
                    "studio": studio_score,
                    "rating": rating_score,
                    "episode": episode_score,
                    "community": community,
                },
            }
        )

    ranked.sort(
        key=lambda item: (
            item["score"],
            item["anime"].get("averageScore", 0) or 0,
        ),
        reverse=True,
    )

    return ranked[:top_n]
