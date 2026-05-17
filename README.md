# Backtesting Framework

Framework Python para testar estratégias de trading com rigor estatístico. O objetivo central é eliminar os vieses que invalidam backtests — look-ahead bias, overfitting in-sample, fee inconsistente — por design, não por convenção.

---

## Por que esse framework existe

Todo backtest ingênuo mente. Os problemas mais comuns:

- Threshold calibrado no dataset completo → look-ahead bias
- Resultado reportado é in-sample → overfit garantido
- Fee aplicada só quando conveniente → retorno irreal
- Nenhum benchmark → não há como saber se a estratégia tem edge real

Esse framework foi construído para tornar esses erros impossíveis de cometer por acidente.

---

## Estrutura do projeto

```
backtester/
├── data/
│   ├── loader.py          # Carrega parquet locais
│   ├── fetcher.py         # Busca dados de exchanges com retry
│   └── validator.py       # Detecta gaps, NaN e duplicatas
│
├── core/
│   ├── types.py           # Signal, Trade, BacktestResult, Direction
│   ├── backtest_engine.py # Loop de execução de trades (uso interno)
│   ├── walk_forward.py    # Walk-forward validation — entry point principal
│   └── fee_model.py       # Fee + slippage, sempre aplicada
│
├── strategy/
│   ├── base.py            # Interface abstrata Strategy
│   └── examples/
│       └── funding_rate.py # Estratégia H3 como referência
│
├── metrics/
│   ├── performance.py     # Win rate, Sharpe, Sortino, profit factor
│   ├── statistical.py     # t-test unilateral, p-value, IC 95%
│   └── risk.py            # Drawdown, MAE, sequência de losses
│
├── report/
│   ├── generator.py       # Gera relatório markdown automaticamente
│   └── templates/
│       └── sprint_report.md
│
├── config.py              # Parâmetros globais com defaults razoáveis
└── run.py                 # CLI
```

---

## Como usar

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Implementar uma estratégia

Crie uma classe que herda de `Strategy` e implemente os quatro métodos obrigatórios:

```python
from backtester.strategy.base import Strategy
from backtester.core.types import Signal, Direction

class MinhaEstrategia(Strategy):

    def name(self) -> str:
        return "minha_estrategia_v1"

    def warmup_periods(self) -> int:
        # candles descartados antes do primeiro sinal
        return 50

    def holding_periods(self) -> int:
        # candles de holding após entrada
        return 4

    def fit(self, train_data) -> None:
        # calibra parâmetros SÓ com dados de treino
        self.threshold = train_data['minha_feature'].quantile(0.95)

    def generate_signals(self, data) -> list:
        signals = []
        for ts, row in data.iterrows():
            if row['minha_feature'] > self.threshold:
                signals.append(Signal(
                    timestamp=ts,
                    direction=Direction.SHORT,
                    confidence=1.0,
                    metadata={'feature': row['minha_feature']}
                ))
        return signals
```

### Rodar via CLI

```bash
# Walk-forward com relatório
python run.py --strategy funding_rate --data btc_4h_2y.parquet --report

# Parâmetros customizados
python run.py --strategy funding_rate --train 600 --test 150 --fee 0.001

# Listar estratégias disponíveis
python run.py --list
```

### Rodar via código

```python
from backtester.core.walk_forward import walk_forward, WalkForwardConfig
from backtester.core.fee_model import FeeModel
from backtester.data.loader import load_parquet
from backtester.strategy.examples.funding_rate import FundingRateStrategy

data = load_parquet("data/btc_4h_2y.parquet")

results = walk_forward(
    data=data,
    strategy=FundingRateStrategy(),
    fee_model=FeeModel(taker_fee=0.001),
    config=WalkForwardConfig(train_size=500, test_size=100, step_size=100),
)
```

---

## Garantias do framework

| Garantia | Implementação |
|---|---|
| Sem look-ahead bias | `fit()` recebe apenas dados de treino. A separação é feita pelo framework, a estratégia não controla isso. |
| Resultado sempre OOS | Todos os `BacktestResult` têm `is_oos=True`. Resultado in-sample é diagnóstico, nunca o resultado principal. |
| Fee sempre aplicada | `fee_model.apply()` é chamado em todos os trades, wins e losses, sem exceção. |
| Warmup garantido | Framework descarta `warmup_periods()` candles antes do primeiro sinal. |
| t-test unilateral | Teste de hipótese é sempre H1: retorno > 0, nunca bilateral. |
| Benchmarks obrigatórios | Todo resultado inclui comparação com buy-and-hold, random entry e estratégia invertida. |
| Reprodutível | Seed fixa (`random_seed=42`), sem randomização oculta. |

---

## Métricas geradas

### Performance
- Win rate, retorno médio/mediano, retorno total
- Sharpe ratio, Sortino ratio
- Profit factor, win/loss ratio
- Trades por dia

### Risco
- Max drawdown
- Maior sequência de losses consecutivos
- Max adverse excursion (MAE), MAE médio e p90
- Capital mínimo atingido na simulação

### Estatística
- t-statistic, p-value (unilateral)
- Intervalo de confiança 95%
- Significância por janela do walk-forward

---

## Relatório automático

Cada execução gera um relatório markdown com:

1. Configuração da execução
2. Resultados por janela do walk-forward
3. Significância estatística global OOS
4. Métricas de risco
5. Comparação com todos os baselines
6. **Conclusão automática** baseada em critérios objetivos:
   - p-value OOS < 0.05
   - Win rate OOS > 52%
   - Edge OOS > 0 após fee
   - Supera random entry com significância
   - Max drawdown < 25%

---

## O que está fora do escopo v1.0

| Feature | Motivo |
|---|---|
| Posições simultâneas | Complexidade sem necessidade no MVP |
| Stop loss / take profit | Adicionar após validar holding fixo |
| Alavancagem | Multiplicador simples, não precisa estar no framework |
| Otimização de parâmetros | Risco de overfit — walk-forward é o controle suficiente |
| UI / Dashboard | Relatório markdown é suficiente |

---

## Configuração padrão

Definida em `config.py`. Todos os parâmetros têm defaults razoáveis:

```python
taker_fee = 0.001            # 0.10% por lado
slippage_estimate = 0.0      # calibrar com dados reais de execução
train_size = 500             # candles de treino por janela
test_size = 100              # candles de teste por janela
step_size = 100              # avanço entre janelas
min_trades_per_window = 10   # janelas com menos trades são descartadas
p_value_threshold = 0.05
min_win_rate = 0.52
max_acceptable_drawdown = -0.25
random_entry_simulations = 100
random_seed = 42
```

---

## Critério de sucesso

O framework está pronto quando uma estratégia nova pode ser testada em menos de 1 hora de trabalho: implementar a interface, rodar o walk-forward, e ter um relatório com conclusão automática.
