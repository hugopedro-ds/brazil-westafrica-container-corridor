# ===========================================================
# Brazil -> West & Central Atlantic Africa — Trade Analysis
# Fonte: ComexStat / MDIC 2025 (exportações marítimas)
# Parte do projeto Brazilian Maritime Analysis
# ===========================================================

import sys
from pathlib import Path

# --- Verificar dependências ----------------------------------
faltam = []
try:
    import pandas as pd
except ImportError:
    faltam.append("pandas")
try:
    import numpy as np
except ImportError:
    faltam.append("numpy")
try:
    import matplotlib.pyplot as plt
except ImportError:
    faltam.append("matplotlib")

if faltam:
    print("FALTAM bibliotecas:", ", ".join(faltam))
    print(f"Instala com:  pip install {' '.join(faltam)}")
    sys.exit(1)

# --- Paths dos ficheiros -------------------------------------
DATA_DIR = Path(".")

FILE_PAIS = DATA_DIR / "exp_brasil_westafrica_pais.xlsx"
FILE_NCM  = DATA_DIR / "exp_brasil_westafrica_ncm.xlsx"

# --- Verificar que os ficheiros existem ----------------------
erro = False
for f in [FILE_PAIS, FILE_NCM]:
    if f.exists():
        print(f"[OK]    {f.name}")
    else:
        print(f"[FALTA] {f.name}")
        erro = True

if erro:
    print("\nCorrige os nomes/localização dos ficheiros e corre de novo.")
    sys.exit(1)

print("\nSetup OK — pronto para o Bloco 2.")
# ===========================================================
# BLOCO 2 — Corte do corredor + classificação contentor/granel
# ===========================================================

print("\n" + "=" * 60)
print("BLOCO 2 — Corte do corredor e perfil de transporte")
print("=" * 60)

# --- Carregar dados (exportação marítima, África inteira) ----
df_pais = pd.read_excel(FILE_PAIS)
df_ncm  = pd.read_excel(FILE_NCM)

COL_FOB  = "2025 - Valor US$ FOB"
COL_KG   = "2025 - Quilograma Líquido"
COL_PAIS = "Países"
COL_NCM  = "Código NCM"

# --- Definição do corredor (regra geográfica explícita) ------
# West & Central Atlantic Africa: costa atlântica sub-saariana,
# da Mauritânia a Angola. 20 países. Grafia = nomes ComexStat.
CORREDOR = [
    "Mauritânia", "Cabo Verde", "Senegal", "Gâmbia", "Guiné-Bissau",
    "Guiné", "Serra Leoa", "Libéria", "Costa do Marfim", "Gana",
    "Togo", "Benin", "Nigéria", "Camarões", "Guiné Equatorial",
    "São Tomé e Príncipe", "Gabão", "Congo",
    "Congo, República Democrática", "Angola",
]

# --- Auditoria do corte: o que entra, o que fica de fora -----
no_ficheiro = set(df_pais[COL_PAIS])
em_falta    = sorted(set(CORREDOR) - no_ficheiro)
excluidos   = sorted(no_ficheiro - set(CORREDOR))

print(f"\nCorredor: {len(CORREDOR)} países (costa atlântica, Mauritânia->Angola)")
if em_falta:
    print(f"  AVISO - corredor sem dados no ficheiro: {em_falta}")
print(f"Excluídos ({len(excluidos)} países - resto de África, fora do corredor):")
print("  " + ", ".join(excluidos))

# --- Aplicar o corte aos dois ficheiros ----------------------
df_pais = df_pais[df_pais[COL_PAIS].isin(CORREDOR)].copy()
df_ncm  = df_ncm[df_ncm[COL_PAIS].isin(CORREDOR)].copy()

# --- Capítulo NCM + classificação contentor / granel-tanque --
df_ncm["Cap"]  = df_ncm[COL_NCM].astype(str).str.zfill(8).str[:2]
df_ncm["NCM4"] = df_ncm[COL_NCM].astype(str).str.zfill(8).str[:4]

# Granel/tanque: cereais(10), oleaginosas/soja(12), açúcar(17),
# combustíveis(27) e etanol (NCM 2207). O resto = contentor.
CAPS_GRANEL = {"10", "12", "17", "27"}
mask_granel = df_ncm["Cap"].isin(CAPS_GRANEL) | (df_ncm["NCM4"] == "2207")
df_ncm["tipo"] = np.where(mask_granel, "granel/tanque", "contentor")

# --- Subconjunto de carga contentorizada ---------------------
df_con = df_ncm[df_ncm["tipo"] == "contentor"].copy()

# --- O funil: total -> granel/tanque -> contentor ------------
tot_total  = df_ncm[COL_FOB].sum()
tot_con    = df_con[COL_FOB].sum()
tot_granel = tot_total - tot_con

print(f"\nFUNIL DO CORREDOR (FOB 2025):")
print(f"  Total marítimo         : USD {tot_total:>15,.0f}")
print(f"  Granel/tanque          : USD {tot_granel:>15,.0f}"
      f"  ({tot_granel/tot_total*100:.1f}%)")
print(f"  Contentor (relevante)  : USD {tot_con:>15,.0f}"
      f"  ({tot_con/tot_total*100:.1f}%)")

# --- Reconciliação: ficheiro-país vs ficheiro-NCM ------------
tot_pais = df_pais[COL_FOB].sum()
ok = abs(tot_pais - tot_total) < 1
print(f"\n  Reconciliação país-file vs NCM-file: USD {tot_pais:,.0f}"
      f"  [{'OK' if ok else 'DIVERGÊNCIA'}]")
print(f"  A análise de carriers governa a fatia de contentor "
      f"(USD {tot_con/1e9:.2f}bn).")
# ===========================================================
# BLOCO 3 — Ranking de carga contentorizada por destino
# ===========================================================

print("\n" + "=" * 60)
print("BLOCO 3 — Ranking de contentor + concentracao geografica")
print("=" * 60)

# --- Ranking: FOB de contentor por país ----------------------
# df_con vem do Bloco 2 (corredor, só carga de contentor).
ranking = (df_con
           .groupby(COL_PAIS)
           .agg(fob_con=(COL_FOB, "sum"),
                kg_con=(COL_KG, "sum")))

ranking["pct"]           = ranking["fob_con"] / ranking["fob_con"].sum() * 100
ranking["value_density"] = ranking["fob_con"] / ranking["kg_con"] * 1000  # USD/tonelada
ranking = ranking.sort_values("fob_con", ascending=False)

# --- Concentração geográfica (sobre carga de contentor) ------
shares  = ranking["pct"]
cr3     = shares.head(3).sum()
cr5     = shares.head(5).sum()
hhi_geo = (shares ** 2).sum()

# --- Mostrar resultados --------------------------------------
print(f"\nCarga contentorizada — corredor: USD {ranking['fob_con'].sum():,.0f}\n")
print(f"{'#':<3}{'País':<26}{'FOB contentor':>16}{'%':>7}{'USD/t':>9}")
print("-" * 61)
for i, (pais, row) in enumerate(ranking.iterrows(), 1):
    print(f"{i:<3}{pais:<26}{row['fob_con']:>16,.0f}"
          f"{row['pct']:>6.1f}%{row['value_density']:>9.0f}")
print("-" * 61)

print(f"\nCR3 (top 3):  {cr3:.1f}%")
print(f"CR5 (top 5):  {cr5:.1f}%")
print(f"HHI geografico:  {hhi_geo:.0f}", end="  ")
if hhi_geo < 1500:
    print("(nao-concentrado)")
elif hhi_geo < 2500:
    print("(moderadamente concentrado)")
else:
    print("(muito concentrado)")

rank_ng = list(ranking.index).index("Nigéria") + 1
print(f"\nAngola lidera a carga de contentor com {ranking.loc['Angola','pct']:.0f}%.")
print(f"A Nigéria, #1 por FOB total, cai para #{rank_ng} em contentor"
      f" — o seu volume era sobretudo açúcar a granel.")
# ===========================================================
# BLOCO 4 — Composição da carga de contentor por destino
# ===========================================================

print("\n" + "=" * 60)
print("BLOCO 4 — Composicao da carga de contentor")
print("=" * 60)

# --- Nomes dos capítulos NCM ---------------------------------
CAP_NOMES = {
    "02": "Carne", "03": "Peixe", "04": "Laticínios",
    "09": "Café/especiarias", "16": "Prep. carne/peixe",
    "19": "Prep. de cereais", "22": "Bebidas", "24": "Tabaco",
    "39": "Plásticos", "41": "Peles/couro", "48": "Papel/cartão",
    "72": "Ferro/aço", "73": "Obras de ferro/aço", "84": "Máquinas",
    "85": "Mat. elétrico", "87": "Veículos",
}
nome_cap = lambda c: CAP_NOMES.get(c, f"Cap {c}")

# --- Composição do corredor (carga de contentor) por capítulo
comp_corr   = df_con.groupby("Cap")[COL_FOB].sum().sort_values(ascending=False)
tot_con_fob = comp_corr.sum()

print(f"\nCarga de contentor do corredor, por capítulo NCM (top 8):")
print(f"  {'Capítulo':<22}{'FOB USD':>16}{'%':>8}")
print("  " + "-" * 46)
for cap, val in comp_corr.head(8).items():
    print(f"  {nome_cap(cap):<22}{val:>16,.0f}{val/tot_con_fob*100:>7.1f}%")
print(f"\n  Carne (Cap 02) = {comp_corr.get('02', 0)/tot_con_fob*100:.0f}% da carga de contentor.")
print(f"  É, antes de tudo, um corredor reefer de proteína congelada.")

# --- HHI commodity + carne %, por país (carga de contentor) --
hhi_commodity, meat_pct = {}, {}
for pais in df_con[COL_PAIS].unique():
    sub     = df_con[df_con[COL_PAIS] == pais]
    fob_cap = sub.groupby("Cap")[COL_FOB].sum()
    tot     = fob_cap.sum()
    hhi_commodity[pais] = ((fob_cap / tot * 100) ** 2).sum()
    meat_pct[pais]      = sub[sub["Cap"] == "02"][COL_FOB].sum() / tot * 100

ranking["hhi_commodity"] = pd.Series(hhi_commodity)
ranking["meat_pct"]      = pd.Series(meat_pct)

# --- Perfil por destino (ordem do ranking de contentor) ------
print(f"\n{'País':<26}{'FOB contentor':>15}{'Carne %':>10}{'HHI carga':>11}")
print("-" * 62)
for pais, row in ranking.iterrows():
    print(f"{pais:<26}{row['fob_con']:>15,.0f}"
          f"{row['meat_pct']:>9.0f}%{row['hhi_commodity']:>11.0f}")

# --- Leitura crítica -----------------------------------------
print(f"\nLeitura:")
print(f"  Angola — maior volume de contentor (USD {ranking.loc['Angola','fob_con']/1e6:.0f}M),")
print(f"  carne só {ranking.loc['Angola','meat_pct']:.0f}%: o resto é manufacturado, máquinas,")
print(f"  veículos. Diversificação com substância.")
print(f"  Nigéria — 0% carne: importação de aves proibida desde 2003. O HHI")
print(f"  baixo ({ranking.loc['Nigéria','hhi_commodity']:.0f}) não é força — é volume pequeno espalhado.")
print(f"  Destinos pequenos (Gabão, Guiné) são quase só carne — HHI alto.")
# ===========================================================
# BLOCO 5 — Carga reefer: o corredor de proteína congelada
# ===========================================================

print("\n" + "=" * 60)
print("BLOCO 5 — Carga reefer: o corredor de proteina")
print("=" * 60)

# --- Reefer = carne + peixe (Cap 02 + 03), sobre contentor ---
CAPS_REEFER = ["02", "03"]
reefer_usd = {}
for pais in df_con[COL_PAIS].unique():
    sub = df_con[df_con[COL_PAIS] == pais]
    reefer_usd[pais] = sub[sub["Cap"].isin(CAPS_REEFER)][COL_FOB].sum()

ranking["reefer_usd"] = pd.Series(reefer_usd)
ranking["reefer_pct"] = ranking["reefer_usd"] / ranking["fob_con"] * 100

# --- Reefer no total do corredor -----------------------------
reefer_corr = ranking["reefer_usd"].sum()
print(f"\nReefer (carne + peixe) = USD {reefer_corr:,.0f}")
print(f"  {reefer_corr/ranking['fob_con'].sum()*100:.1f}% de toda a carga de "
      f"contentor do corredor.")
print(f"  O corredor de contentor é, na sua maioria, proteína congelada.")

# --- Reefer por destino (valor absoluto) ---------------------
print(f"\n{'País':<26}{'Reefer USD':>15}{'% do país':>11}")
print("-" * 52)
for pais, row in ranking.sort_values("reefer_usd", ascending=False).iterrows():
    print(f"{pais:<26}{row['reefer_usd']:>15,.0f}{row['reefer_pct']:>10.0f}%")

# --- As duas anomalias que os dados expõem -------------------
print(f"\nDuas anomalias:")
print(f"  Nigéria — reefer {ranking.loc['Nigéria','reefer_pct']:.0f}% "
      f"(USD {ranking.loc['Nigéria','reefer_usd']:,.0f}). A Nigéria proíbe a")
print(f"    importação de aves congeladas desde 2003 — o frango brasileiro")
print(f"    não entra oficialmente no maior mercado da África Ocidental.")
print(f"  Benin — reefer {ranking.loc['Benin','reefer_pct']:.0f}% "
      f"(USD {ranking.loc['Benin','reefer_usd']:,.0f}) num país de ~13M de habitantes.")
print(f"    Cotonou é entreposto conhecido: parte deste frango é")
print(f"    re-exportada para a Nigéria. O 'destino Benin' sobrestima o")
print(f"    consumo real do Benin.")

# --- Angola: líder reefer, mas o menos dependente ------------
print(f"\nAngola — maior volume reefer do corredor "
      f"(USD {ranking.loc['Angola','reefer_usd']:,.0f}), mas reefer é só")
print(f"  {ranking.loc['Angola','reefer_pct']:.0f}% da sua carga: importa proteína "
      f"E manufacturado.")
# ===========================================================
# BLOCO 6 — Matriz de carriers (28 rotas verificadas)
# ===========================================================

print("\n" + "=" * 60)
print("BLOCO 6 — Matriz de carriers: directo vs transbordo")
print("=" * 60)

# --- Matriz de carriers --------------------------------------
# Fonte: pesquisas point-to-point reais nos sites dos 4 maiores
# carriers (Hapag-Lloyd, CMA CGM, Maersk, MSC), Mai-Jul 2026.
# Saída sempre de Santos. "direto" = sem transbordo em hub
# estrangeiro; "transbordo" = via hub estrangeiro.
# transit em dias = Santos -> porto de destino.
matriz_carriers = {
    "Luanda (Angola)": {
        "Hapag-Lloyd": ("direto",     33),
        "CMA CGM":     ("transbordo", 53),
        "Maersk":      ("transbordo", 75),
        "MSC":         ("transbordo", 27),
    },
    "Tema (Gana)": {
        "Hapag-Lloyd": ("transbordo", 33),
        "CMA CGM":     ("transbordo", 35),
        "Maersk":      ("transbordo", 29),
        "MSC":         ("transbordo", 23),
    },
    "Matadi (Congo RDC)": {
        "Hapag-Lloyd": ("transbordo", 44),
        "CMA CGM":     ("transbordo", 71),
        "Maersk":      ("transbordo", 55),
        "MSC":         ("transbordo", 33),
    },
    "Lagos (Nigéria)": {
        "Hapag-Lloyd": ("transbordo", 35),
        "CMA CGM":     ("transbordo", 44),
        "Maersk":      ("transbordo", 38),
        "MSC":         ("transbordo", 30),
    },
    "Pointe-Noire (Congo)": {
        "Hapag-Lloyd": ("transbordo", 41),
        "CMA CGM":     ("transbordo", 54),
        "Maersk":      ("transbordo", 44),
        "MSC":         ("transbordo", 27),
    },
    "Dakar (Senegal)": {
        "Hapag-Lloyd": ("transbordo", 27),
        "CMA CGM":     ("transbordo", 29),
        "Maersk":      ("transbordo", 34),
        "MSC":         ("transbordo", 18),
    },
    "Lomé (Togo)": {
        "Hapag-Lloyd": ("transbordo", 43),
        "CMA CGM":     ("transbordo", 38),
        "Maersk":      ("transbordo", 38),
        "MSC":         ("transbordo", 23),
    },
}

# nº total de rotas verificadas (calculado, nao hardcoded)
n_rotas = sum(len(c) for c in matriz_carriers.values())

# --- Contar diretos vs transbordo ----------------------------
print(f"\n{'Destino':<24}{'Diretos':>9}{'Transbordo':>12}")
print("-" * 45)
total_diretos = 0
for destino, carriers in matriz_carriers.items():
    diretos = sum(1 for tipo, _ in carriers.values() if tipo == "direto")
    transb  = sum(1 for tipo, _ in carriers.values() if tipo == "transbordo")
    total_diretos += diretos
    print(f"{destino:<24}{diretos:>9}{transb:>12}")
print("-" * 45)
rotulo = f"TOTAL ({n_rotas} rotas)"
print(f"{rotulo:<24}{total_diretos:>9}{n_rotas - total_diretos:>12}")

# --- Transit time: Luanda (único destino com directo) --------
luanda   = matriz_carriers["Luanda (Angola)"]
direto_t = [t for tipo, t in luanda.values() if tipo == "direto"]
transb_t = [t for tipo, t in luanda.values() if tipo == "transbordo"]
print(f"\nTransit time Santos -> Luanda:")
print(f"  Directo (Hapag):     {direto_t[0]} dias")
print(f"  Transbordo (range):  {min(transb_t)}-{max(transb_t)} dias"
      f"  (media {sum(transb_t)/len(transb_t):.0f})")
print(f"  O transbordo MSC ({min(transb_t)}d) chega a ser mais rapido que o")
print(f"  directo Hapag ({direto_t[0]}d) na ida. O valor do directo nao e")
print(f"  velocidade -- e servico dedicado, terminal DP World, contrato 10 anos.")

# --- Leitura -------------------------------------------------
ng_rank = list(ranking.index).index("Nigéria") + 1
print(f"\nLeitura:")
print(f"  {total_diretos} rota directa em {n_rotas}. O corredor corre em transbordo.")
print(f"  O unico servico directo (Hapag/Luanda) serve o Angola -- o maior")
print(f"  destino de carga contentorizada do corredor "
      f"({ranking.loc['Angola','pct']:.0f}%).")
print(f"  A Nigeria (#{ng_rank} em contentor) e os outros 5 destinos verificados")
print(f"  dependem todos de transbordo em hub estrangeiro.")
print(f"  Nota: ate a Hapag chega aos dois Congos por transbordo em Luanda --")
print(f"  Luanda funciona como o no de distribuicao da Africa Central.")
# ===========================================================
# BLOCO 7 — Outputs: CSV + gráfico do ranking de contentor
# ===========================================================

print("\n" + "=" * 60)
print("BLOCO 7 — Exportar resultados")
print("=" * 60)

# --- Guardar o ranking completo em CSV -----------------------
OUT_CSV = "ranking_contentor_corredor_2025.csv"
ranking.to_csv(OUT_CSV, encoding="utf-8-sig")
print(f"\n[guardado] {OUT_CSV}  ({len(ranking)} destinos)")

# --- Gráfico de barras: ranking de carga de contentor --------
rk    = ranking.sort_values("fob_con")        # ascendente -> maior no topo
cores = ["#2E8B57" if p == "Angola" else "#9aa7b3" for p in rk.index]

fig, ax = plt.subplots(figsize=(9, 7))
ax.barh(rk.index, rk["fob_con"] / 1e6, color=cores,
        edgecolor="white", linewidth=0.6)
ax.set_xlabel("Carga contentorizada — FOB (USD milhões)")
ax.set_title("Brasil -> West & Central Atlantic Africa\n"
             "Ranking de carga contentorizada por destino, 2025")
ax.set_xlim(0, rk["fob_con"].max() / 1e6 * 1.12)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(True, axis="x", alpha=0.3)
ax.set_axisbelow(True)

for i, (pais, row) in enumerate(rk.iterrows()):
    ax.text(row["fob_con"] / 1e6 + 4, i, f"{row['fob_con']/1e6:.0f}",
            va="center", fontsize=8, color="#5D6D7E")

plt.tight_layout()
OUT_PNG = "ranking_contentor.png"
plt.savefig(OUT_PNG, dpi=150)
plt.close(fig)
print(f"[guardado] {OUT_PNG}")
# ============================================================
# BLOCO 8 — Gráfico do post: ranking de contentor
# Barras horizontais empilhadas, estilo da série LinkedIn
# ============================================================
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.patches import Patch

print("\n" + "=" * 60)
print("BLOCO 8 — Grafico do post")
print("=" * 60)

rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]

# paleta da série
C_TITULO, C_SUBTIT, C_LEVE = "#0F1419", "#3D4F5E", "#5D6D7E"
C_RODAPE, C_LINHA, C_TEXTO = "#7B8A9A", "#D5DBE0", "#2C3E50"
C_DIRETO, C_TRANSB = "#2E8B57", "#C0392B"
ARQ_SAIDA = "grafico_westafrica_post.png"

# --- 8.1 categorias de carga (capítulo NCM -> categoria) -----
def categoria(cap):
    if cap == "02":               return "meat"
    if cap in ("03", "16"):       return "protein2"
    if cap in ("72", "73"):       return "steel"
    if cap in ("84", "85", "87"): return "equip"
    return "others"

ORDEM_CAT = ["meat", "protein2", "steel", "equip", "others"]
CAT_COR = {"meat": "#2f6fb0", "protein2": "#6aaed6", "steel": "#7d5ba6",
           "equip": "#d1603d", "others": "#d9d9d9"}
CAT_LABEL = {"meat": "Frozen meat", "protein2": "Fish & prepared",
             "steel": "Iron & steel", "equip": "Machinery & vehicles",
             "others": "Other cargo"}

# --- 8.2 nomes EN + serviço verificado -----------------------
NOME_EN = {
    "Angola": "Angola", "Gana": "Ghana", "Nigéria": "Nigeria",
    "Congo, República Democrática": "DR Congo", "Congo": "Congo",
    "Gabão": "Gabon", "Guiné": "Guinea", "Costa do Marfim": "Ivory Coast",
    "Libéria": "Liberia", "Senegal": "Senegal", "Serra Leoa": "Sierra Leone",
    "Benin": "Benin", "Togo": "Togo", "Camarões": "Cameroon",
    "Mauritânia": "Mauritania", "Gâmbia": "Gambia", "Cabo Verde": "Cape Verde",
    "Guiné Equatorial": "Eq. Guinea", "Guiné-Bissau": "Guinea-Bissau",
    "São Tomé e Príncipe": "São Tomé",
}
SERVICO = {
    "Angola": "direto", "Gana": "transbordo", "Nigéria": "transbordo",
    "Senegal": "transbordo", "Congo": "transbordo",
    "Congo, República Democrática": "transbordo", "Togo": "transbordo",
}
COR_SERVICO = {"direto": C_DIRETO, "transbordo": C_TRANSB}

# --- 8.3 dados: top 12 destinos + composição da carga --------
N_TOP = 12
top = ranking.head(N_TOP).index.tolist()          # ranking vem do Bloco 3

dfc = df_con.copy()
dfc["cat"] = dfc["Cap"].map(categoria)
comp = dfc.groupby([COL_PAIS, "cat"])[COL_FOB].sum().unstack(fill_value=0)
for c in ORDEM_CAT:
    if c not in comp.columns:
        comp[c] = 0.0
comp = comp.loc[top, ORDEM_CAT] / 1e6             # USD milhões

fob_top   = ranking.loc[top, "fob_con"] / 1e6
share_top = ranking.head(N_TOP)["fob_con"].sum() / ranking["fob_con"].sum() * 100

# --- 8.4 figura: barras horizontais empilhadas ---------------
fig_w, fig_h = 12.0, 7.6
fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=100)
fig.patch.set_facecolor("#FFFFFF")
ax.set_facecolor("#FFFFFF")
fig.subplots_adjust(top=0.82, bottom=0.27, left=0.16, right=0.94)

y = list(range(len(top)))
esq = [0.0] * len(top)
for cat in ORDEM_CAT:
    larg = comp[cat].values
    ax.barh(y, larg, left=esq, height=0.66, color=CAT_COR[cat],
            edgecolor="white", linewidth=0.6)
    esq = [e + w for e, w in zip(esq, larg)]

ax.set_yticks(y)
ax.set_yticklabels([NOME_EN.get(p, p) for p in top], fontsize=10.5)
ax.invert_yaxis()
ax.set_xlim(0, fob_top.max() * 1.13)

# nome do país colorido pelo serviço verificado
for tick, p in zip(ax.get_yticklabels(), top):
    tick.set_color(COR_SERVICO[SERVICO[p]] if p in SERVICO else C_TEXTO)

# rótulo de valor (FOB total) no fim de cada barra
for i, p in enumerate(top):
    ax.text(fob_top.iloc[i] + fob_top.max() * 0.012, i,
            f"{fob_top.iloc[i]:.0f}", va="center", ha="left",
            fontsize=9.5, fontweight="bold", color=C_TEXTO)

# --- 8.5 eixo ------------------------------------------------
ax.set_xlabel("Containerised exports — FOB (USD millions)",
              fontsize=10.5, color=C_SUBTIT, labelpad=8)
ax.tick_params(axis="x", colors=C_LEVE, labelsize=9.5)
ax.tick_params(axis="y", length=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(C_LINHA)
ax.grid(True, axis="x", linestyle=":", linewidth=0.7, color=C_LINHA, alpha=0.7)
ax.set_axisbelow(True)

# --- 8.6 título (3 linhas, estilo da série) ------------------
fig.text(0.5, 0.950,
         "Brazil → West & Central Africa: a USD 1.8bn container corridor.",
         fontsize=17, fontweight="bold", color=C_TITULO, ha="center")
fig.text(0.5, 0.908,
         "Angola leads it — and runs the only direct service on the coast.",
         fontsize=13, color=C_SUBTIT, ha="center")
fig.text(0.5, 0.866,
         "Containerised maritime exports by destination, 2025  ·  part of a "
         "USD 5.0bn corridor — 64% bulk sugar, grain & fuel excluded",
         fontsize=10, color=C_LEVE, ha="center", style="italic")

# --- 8.7 legenda de carga (5 categorias) ---------------------
handles = [Patch(facecolor=CAT_COR[c], edgecolor="white", label=CAT_LABEL[c])
           for c in ORDEM_CAT]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.170),
           ncol=5, frameon=False, fontsize=9, handlelength=1.5,
           columnspacing=2.2)

# --- 8.8 nota de serviço (nome verde/vermelho) ---------------
segs = [
    ("Destination in ", C_LEVE),
    ("green", C_DIRETO),
    (" = direct service     ·     in ", C_LEVE),
    ("red", C_TRANSB),
    (" = transshipment     ·     grey = not in the carrier matrix", C_LEVE),
]
fig.canvas.draw()
rend = fig.canvas.get_renderer()
fw = fig.bbox.width
tmp = [fig.text(0, 0, t, fontsize=9) for t, _ in segs]
larg = [a.get_window_extent(rend).width / fw for a in tmp]
for a in tmp:
    a.remove()
xx = 0.5 - sum(larg) / 2
for (t, c), lw in zip(segs, larg):
    fig.text(xx, 0.130, t, ha="left", va="center", fontsize=9, color=c)
    xx += lw

# --- 8.9 rodapé (estilo da série) ----------------------------
fig.add_artist(plt.Line2D([0.075, 0.94], [0.098, 0.098],
                          color=C_LINHA, linewidth=0.8, transform=fig.transFigure))
fig.text(0.5, 0.065,
         f"Scope:  Top {N_TOP} of 20 corridor destinations "
         f"({share_top:.0f}% of container value)  ·  Container-relevant cargo = "
         f"maritime exports minus bulk sugar, grain, soy, fuel & ethanol  ·  "
         f"Carrier matrix: 4 carriers × 7 destinations = 28 routes",
         ha="center", fontsize=7.5, color=C_LEVE)
fig.text(0.075, 0.030,
         "Source:  ComexStat / MDIC 2025  ·  Carrier schedules verified "
         "May-Jul 2026: Hapag-Lloyd, Maersk, CMA CGM, MSC",
         ha="left", fontsize=8, color=C_RODAPE)
fig.text(0.94, 0.030, "github.com/hugopedro-ds/brazilian-maritime-analysis-2025",
         ha="right", fontsize=8, color=C_RODAPE)

fig.savefig(ARQ_SAIDA, dpi=150, facecolor="#FFFFFF", edgecolor="none")
print("Grafico salvo:", ARQ_SAIDA)