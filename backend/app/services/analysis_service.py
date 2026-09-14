from app.domain.market import Market


class AnalysisGenerator:
    """Deterministic Spanish presentation; every value comes from structured data."""

    def generate(self, prediction: dict | None, comparison: dict | None = None) -> dict:
        if not prediction or not prediction.get("goals", {}).get("probabilities"):
            return {
                "paragraphs": [
                    "No hay suficientes datos anteriores al inicio para estimar una probabilidad de goles. El partido permanece visible en la cartelera."
                ],
                "factors": [
                    {"category": "FORM", "direction": "negative", "text": "Muestra insuficiente"}
                ],
            }
        features, goals = prediction["features"], prediction["goals"]
        market = Market.OVER_2_5_GOALS.value
        probability = goals["probabilities"].get(market)
        paragraphs, factors = [], []
        if probability is not None:
            paragraphs.append(
                f"El ensemble estima una probabilidad del {probability:.1%} de superar 2,5 goles. Es una estimación estadística, no un resultado asegurado."
            )
        home, away = features["home"]["10"], features["away"]["10"]
        if home["sample_size"] and away["sample_size"]:
            paragraphs.append(
                f"El local registra {home['total_goals_average']:.2f} goles totales de media en sus últimos {home['sample_size']} partidos; el visitante, {away['total_goals_average']:.2f} en {away['sample_size']}. Las tasas Over 2,5 son {home['over25_rate']:.1%} y {away['over25_rate']:.1%}, respectivamente."
            )
            factors.extend(
                [
                    {
                        "category": "FORM",
                        "direction": "positive"
                        if min(home["over25_rate"], away["over25_rate"]) >= 0.6
                        else "neutral",
                        "text": f"Over 2,5 reciente: local {home['over25_rate']:.1%}, visitante {away['over25_rate']:.1%}.",
                    },
                    {
                        "category": "ATTACK",
                        "direction": "neutral",
                        "text": f"Goles a favor: {home['goals_for']:.2f} local / {away['goals_for']:.2f} visitante.",
                    },
                    {
                        "category": "DEFENCE",
                        "direction": "neutral",
                        "text": f"Goles concedidos: {home['goals_against']:.2f} local / {away['goals_against']:.2f} visitante.",
                    },
                ]
            )
        hs, aws = features["home_split"], features["away_split"]
        if hs["sample_size"] and aws["sample_size"]:
            sentence = f"Solo en casa/fuera, las tasas Over 2,5 son {hs['over25_rate']:.1%} para el local ({hs['sample_size']} partidos) y {aws['over25_rate']:.1%} para el visitante ({aws['sample_size']} partidos)."
            paragraphs.append(sentence)
            factors.append(
                {
                    "category": "HOME_AWAY",
                    "direction": "positive"
                    if min(hs["over25_rate"], aws["over25_rate"]) >= 0.6
                    else "neutral",
                    "text": sentence,
                }
            )
        models = [
            f"{model['name']}: {model['probabilities'][market]:.1%}"
            for model in goals["models"]
            if model["status"] == "available" and market in model["probabilities"]
        ]
        paragraphs.append("Estimaciones de los modelos: " + "; ".join(models) + ".")
        for model in goals["models"]:
            if model["name"] == "xg" and model["status"] == "unavailable":
                factors.append(
                    {
                        "category": "XG",
                        "direction": "negative",
                        "text": "xG real no disponible con una muestra suficiente; su peso se redistribuye.",
                    }
                )
        league = features.get("league")
        factors.append(
            {
                "category": "LEAGUE",
                "direction": "neutral" if league else "negative",
                "text": f"Contexto de competición: {league['total_goals_average']:.2f} goles, muestra {league['sample_size']}."
                if league
                else "No hay muestra suficiente para contextualizar la liga.",
            }
        )
        h2h = features["h2h"]["summary"]
        if h2h["sample_size"]:
            factors.append(
                {
                    "category": "H2H",
                    "direction": "negative" if h2h["over25_rate"] < 0.4 else "neutral",
                    "text": f"H2H: {h2h['over25_rate']:.1%} Over 2,5 en {h2h['sample_size']} encuentros. Contexto descriptivo, sin peso adicional en el ensemble.",
                }
            )
        consensus = goals["consensus"].get(market)
        if consensus:
            factors.append(
                {
                    "category": "MODEL_CONSENSUS",
                    "direction": "positive"
                    if consensus["model_disagreement"] == "LOW"
                    else "negative",
                    "text": f"Desacuerdo {consensus['model_disagreement']}; desviación entre modelos {consensus['model_std'] * 100:.1f} puntos porcentuales.",
                }
            )
        if comparison:
            available = [
                f"{book}: {quote['decimal_odds']:.2f}{' (STALE)' if quote['stale'] else ''}"
                for book, quote in comparison["quotes"].items()
                if quote
            ]
            if available:
                paragraphs.append("Cuotas observadas: " + ", ".join(available) + ".")
            if comparison.get("best"):
                best = comparison["best"]
                paragraphs.append(
                    f"La mejor cuota disponible es {best['decimal_odds']:.2f} en {best['bookmaker']}, frente a una cuota justa de {comparison['fair_odds']:.2f}. El EV bruto del modelo es {best['ev']:.1%}; no incluye posibles comisiones de Exchange."
                )
            else:
                paragraphs.append("No hay cuotas comparables disponibles para este mercado.")
        grade = prediction["confidence"].get(market, {"category": "INSUFFICIENT", "score": 0})
        paragraphs.append(
            f"Confianza {grade['category']} ({grade['score']:.0f}/100). Calidad {prediction['quality']['category']} ({prediction['quality']['score']:.0f}/100)."
        )
        return {"paragraphs": paragraphs, "factors": factors}
