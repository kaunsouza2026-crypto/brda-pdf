import os
import re
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    Flowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# CONFIGURAÇÕES DE PASTAS E ARQUIVOS
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PASTA_LOGOS = "assets/logos"
LOGO_CABECALHO = "logo_cabecalho.png"
LOGO_RODAPE = "logo_rodape.png"
LOGO_MARCA_DAGUA = "marca_dagua.png"
QRCODE = "qrcode.png"

st.set_page_config(
    page_title="Atualizador de PDF Cadastral",
    page_icon="📄",
    layout="centered"
)

st.markdown("""
    <style>
    .main {
        background-color: #0d1117;
    }
    .stTextArea textarea {
        background-color: #161b22;
        color: #ffffff;
        border: 1px solid #30363d;
    }
    .stTextInput input {
        background-color: #161b22;
        color: #ffffff;
        border: 1px solid #30363d;
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
    .subtext {
        color: #8b949e;
        text-align: center;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Atualizador de PDF Cadastral</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtext'>Escolha entre preencher manualmente ou colar os dados da ficha</p>", unsafe_allow_html=True)

# OPÇÃO DE ESCOLHA: COLAR OU MANUAL
modo_entrada = st.radio("Selecione o modo de preenchimento:", ["Colar Ficha (Automático)", "Preencher Manualmente"], horizontal=True)

# FUNÇÃO DE EXTRAÇÃO INTELIGENTE (só os campos do PDF)
def extrair_dados_ficha(texto_ficha):
    dados = {
        "Razão Social": "NÃO IDENTIFICADO",
        "CNPJ": "00.000.000/0000-00",
        "Situação": "ATIVA",
        "CPF Master": "",
        "Usuário(s)": "",
    }

    if not texto_ficha.strip():
        return dados

    texto_ficha = texto_ficha.replace("\\", "/")

    # ---------- FORMATO PIPE (agencia|conta|cnpj|razao|cpf|nome|telefone|usuario) ----------
    partes = [p.strip() for p in texto_ficha.replace("\n", "").split("|")]
    if len(partes) >= 6 and any(re.fullmatch(r"\d{14}", p) for p in partes):
        for i, p in enumerate(partes):
            # CNPJ (14 dígitos)
            if re.fullmatch(r"\d{14}", p):
                c = p
                dados["CNPJ"] = f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
                # Razão Social costuma vir logo depois do CNPJ
                if i + 1 < len(partes) and not re.fullmatch(r"[\d.\-/]+", partes[i + 1]):
                    dados["Razão Social"] = partes[i + 1]
            # CPF (11 dígitos)
            elif re.fullmatch(r"\d{11}", p) and len(partes) > i and i > 0:
                # pula se parecer telefone (termina em 0000-9999 range) — CPF vem antes do nome
                if i + 1 < len(partes) and len(partes[i + 1].split()) >= 2:
                    cpf = p
                    dados["CPF Master"] = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
            # Usuário (letras+dígitos com maiúsculas tipo JMEM00025)
            elif re.fullmatch(r"[A-Z]{2,}[A-Z0-9]*\d+", p) and not p.startswith("R$"):
                if not dados["Usuário(s)"]:
                    dados["Usuário(s)"] = p
        dados["Situação"] = "ATIVA"
        return dados

    # Razão Social
    match_empresa = re.search(r"Empresa[:\s]+([^\n]+)", texto_ficha, re.IGNORECASE)
    if match_empresa:
        dados["Razão Social"] = match_empresa.group(1).strip()
    else:
        match_razao = re.search(r"RAZ[ÃA]O SOCIAL[:\s]+([^\n]+)", texto_ficha, re.IGNORECASE)
        if match_razao:
            dados["Razão Social"] = match_razao.group(1).strip()
        else:
            match_razao2 = re.search(r"\[\d+\|\d+-[0-9X]\]\s*-\s*\[\d+\]\s*-\s*\[([^\]]+)\]", texto_ficha)
            if match_razao2:
                dados["Razão Social"] = match_razao2.group(1).strip()
            else:
                match_nome = re.search(r"Nome:\s*([^|]+)", texto_ficha, re.IGNORECASE)
                if match_nome:
                    dados["Razão Social"] = match_nome.group(1).strip()

    # CNPJ
    match_cnpj = re.search(r"CNPJ[:\s]+([\d./-]+)", texto_ficha, re.IGNORECASE)
    if match_cnpj:
        c_limpo = re.sub(r"\D", "", match_cnpj.group(1))
        if len(c_limpo) == 14:
            dados["CNPJ"] = f"{c_limpo[:2]}.{c_limpo[2:5]}.{c_limpo[5:8]}/{c_limpo[8:12]}-{c_limpo[12:]}"
    if dados["CNPJ"] == "00.000.000/0000-00":
        match_cnpj2 = re.search(r"\[(\d{14})\]", texto_ficha)
        if not match_cnpj2:
            match_cnpj2 = re.search(r"\b(\d{14})\b", texto_ficha)
        if match_cnpj2:
            c = match_cnpj2.group(1)
            dados["CNPJ"] = f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

    # CPF Master (sócio da ficha nova ou usuário master antiga)
    match_cpf_socio = re.search(r"CPF[:\s]*(\d{11})", texto_ficha, re.IGNORECASE)
    if match_cpf_socio:
        cpf = match_cpf_socio.group(1)
        dados["CPF Master"] = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    else:
        match_cpf_master = re.search(r"CPF USU[ÁA]RIO MASTER[:\s]+([\d.-]+)", texto_ficha, re.IGNORECASE)
        if match_cpf_master:
            cpf_limpo = re.sub(r"\D", "", match_cpf_master.group(1))
            if len(cpf_limpo) == 11:
                dados["CPF Master"] = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"

    # Usuário(s)
    match_usuario = re.search(r"Usu[áa]rio[:\s]+([A-Za-z0-9]+)", texto_ficha, re.IGNORECASE)
    if match_usuario:
        dados["Usuário(s)"] = match_usuario.group(1).strip()
    if not dados["Usuário(s)"]:
        matches_user = re.findall(r"USU[ÁA]RIOS?[:\s]+([A-Za-z0-9]+)", texto_ficha, re.IGNORECASE)
        for val_user in matches_user:
            val_user_limpo = val_user.strip()
            if val_user_limpo and val_user_limpo.upper() != "MASTER":
                dados["Usuário(s)"] = val_user_limpo
                break

    # Situação sempre ATIVA
    dados["Situação"] = "ATIVA"

    return dados

class CheckVerde(Flowable):
    def __init__(self, tamanho=10):
        Flowable.__init__(self)
        self.tamanho = tamanho
        self.width = tamanho
        self.height = tamanho

    def draw(self):
        c = self.canv
        s = self.tamanho
        r = s / 2
        c.saveState()
        c.setFillColor(colors.HexColor("#00A859"))
        c.circle(r, r, r, fill=1, stroke=0)
        c.setStrokeColor(colors.white)
        c.setLineWidth(1.4)
        c.setLineCap(1)
        c.line(s * 0.28, s * 0.48, s * 0.42, s * 0.32)
        c.line(s * 0.42, s * 0.32, s * 0.72, s * 0.68)
        c.restoreState()

class LinhaVertical(Flowable):
    def __init__(self, altura=38, cor="#B0B0B0", largura_linha=1):
        Flowable.__init__(self)
        self.altura = altura
        self.cor = cor
        self.largura_linha = largura_linha
        self.width = largura_linha
        self.height = altura

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(colors.HexColor(self.cor))
        c.setLineWidth(self.largura_linha)
        c.line(0, 0, 0, self.altura)
        c.restoreState()

def caminho_logo(pasta_script, nome):
    return os.path.join(pasta_script, PASTA_LOGOS, nome)

def carregar_imagem(caminho, largura=None, altura=None):
    if os.path.exists(caminho):
        img = Image(caminho)
        if altura and not largura:
            fator = altura / float(img.imageHeight)
            img.drawWidth = img.imageWidth * fator
            img.drawHeight = altura
        elif largura and not altura:
            fator = largura / float(img.imageWidth)
            img.drawWidth = largura
            img.drawHeight = img.imageHeight * fator
        elif largura and altura:
            img.drawWidth = largura
            img.drawHeight = altura
        return img
    return Spacer(largura or 100, altura or 30)

def adicionar_marca_dagua(canvas, doc):
    caminho = caminho_logo(PASTA_SCRIPT, LOGO_MARCA_DAGUA)
    if not os.path.exists(caminho):
        caminho = caminho_logo(PASTA_SCRIPT, LOGO_RODAPE)
    canvas.saveState()
    try:
        canvas.setFillAlpha(0.05)
        canvas.setStrokeAlpha(0.05)
    except AttributeError:
        pass
    largura_item, altura_item, passo_x, passo_y = 130, 120, 130, 120
    if os.path.exists(caminho):
        row_idx = 0
        for y in range(-20, int(A4[1]) + 70, passo_y):
            offset_x = (row_idx % 2) * (passo_x / 2)
            for x in range(-80, int(A4[0]) + 100, passo_x):
                canvas.drawImage(caminho, x + offset_x, y, width=largura_item, height=altura_item, mask="auto", preserveAspectRatio=True)
            row_idx += 1
    canvas.restoreState()

def gerar_pdf(pasta_script, dados_empresa):
    razao = dados_empresa["Razão Social"]
    razao_limpa = re.sub(r'[\\/*?:"<>|]', "", razao)
    nome_pdf = f"ATUALIZAÇÃO CADASTRAL - {razao_limpa}.pdf"
    caminho_pdf = os.path.join(pasta_script, nome_pdf)

    doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    story = []
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=13.5, leading=16, fontName="Helvetica-Bold", textColor=colors.HexColor("#111111"))
    estilo_sub = ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=colors.HexColor("#222222"))
    estilo_secao = ParagraphStyle("Secao", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))
    estilo_texto = ParagraphStyle("Texto", parent=styles["Normal"], fontSize=9.5, leading=13.5, textColor=colors.HexColor("#444444"))
    estilo_topico = ParagraphStyle("Topico", parent=styles["Normal"], fontSize=9.5, leading=14, textColor=colors.HexColor("#333333"))
    estilo_qr_legenda = ParagraphStyle("QRLegenda", parent=styles["Normal"], fontSize=8, leading=10, alignment=1, textColor=colors.HexColor("#666666"))

    logo_topo = carregar_imagem(caminho_logo(pasta_script, LOGO_CABECALHO), altura=68)
    linha_divisoria = LinhaVertical(altura=60, cor="#B0B0B0", largura_linha=1)
    p_titulo = Paragraph("COMUNICADO IMPORTANTE", estilo_titulo)

    cab = Table([[logo_topo, linha_divisoria, p_titulo]], colWidths=[200, 25, 270])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(cab)
    story.append(Spacer(1, 22))

    story.append(Paragraph("ATUALIZAÇÃO CADASTRAL", estilo_sub))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Em conformidade com as diretrizes de autorregulação bancária e as boas práticas estabelecidas pelo sistema financeiro nacional, comunicamos que a atualização cadastral de empresas junto ao Internet Banking Empresarial é procedimento obrigatório e periódico.", estilo_texto))
    story.append(Spacer(1, 18))

    story.append(Paragraph("DADOS DO MASTER:", estilo_secao))
    story.append(Spacer(1, 6))
    
    tabela = []
    for k, v in dados_empresa.items():
        if v is not None:
            tabela.append([Paragraph(f"<b>{k}:</b>", estilo_texto), Paragraph(str(v), estilo_texto)])

    t = Table(tabela, colWidths=[100, 385])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    story.append(t)
    story.append(Spacer(1, 18))

    story.append(Paragraph("A atualização cadastral tem como finalidade:", estilo_texto))
    story.append(Spacer(1, 8))

    check = CheckVerde(tamanho=10)
    for item in [
        "Garantir a segurança das operações financeiras;",
        "Manter os dados da empresa e de seus representantes legais atualizados;",
        "Atender às exigências regulatórias vigentes;",
        "Prevenir fraudes e inconsistências cadastrais.",
    ]:
        row = Table([[check, Paragraph(item, estilo_topico)]], colWidths=[18, 467])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4)]))
        story.append(row)

    story.append(Spacer(1, 18))
    story.append(Paragraph("Reforçamos que a não realização da atualização dentro do prazo estabelecido poderá acarretar restrições operacionais, incluindo limitações temporárias de acesso a determinados serviços bancários.", estilo_texto))
    story.append(Spacer(1, 14))
    story.append(Paragraph("A atualização pode ser realizada diretamente pelo Bradesco Net Empresas, acessando o menu de Cadastro/Atualização Cadastral, ou mediante comparecimento à agência de relacionamento.", estilo_texto))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Em caso de dúvidas, recomenda-se entrar em contato com seu gerente de contas ou com a central de atendimento empresarial.", estilo_texto))
    story.append(Spacer(1, 25))

    img_rodape = carregar_imagem(caminho_logo(pasta_script, LOGO_RODAPE), altura=75)
    img_qr = carregar_imagem(caminho_logo(pasta_script, QRCODE), largura=110, altura=110)
    p_legenda_qr = Paragraph("Escaneie o QR Code para acessar o portal", estilo_qr_legenda)

    bloco_qr = Table([[img_qr], [Spacer(1, 4)], [p_legenda_qr]], colWidths=[140])
    bloco_qr.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

    rod = Table([["", img_rodape, bloco_qr, ""]], colWidths=[95, 145, 140, 125])
    rod.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("ALIGN", (2, 0), (2, 0), "LEFT"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(rod)

    doc.build(story, onFirstPage=adicionar_marca_dagua, onLaterPages=adicionar_marca_dagua)
    return caminho_pdf

# INTERFACE DO STREAMLIT
dados_iniciais = {
    "Razão Social": "",
    "CNPJ": "",
    "Situação": "ATIVA",
    "CPF Master": "",
    "Usuário(s)": "",
}

if modo_entrada == "Colar Ficha (Automático)":
    ficha_input = st.text_area("COLE A FICHA DO CLIENTE AQUI", placeholder="Cole a linha ou o bloco de texto da ficha...", height=120)
    if st.button("Processar Ficha", type="primary"):
        if ficha_input.strip():
            st.session_state['dados_empresa'] = extrair_dados_ficha(ficha_input)
            st.success("Ficha lida e dados extraídos com sucesso!")
        else:
            st.warning("Por favor, cole uma ficha na caixa de texto acima.")
else:
    if 'dados_empresa' not in st.session_state:
        st.session_state['dados_empresa'] = dados_iniciais

if 'dados_empresa' in st.session_state:
    dados = st.session_state['dados_empresa']
    st.markdown("---")
    st.subheader("DADOS PARA O PDF")
    
    col1, col2 = st.columns(2)
    with col1:
        razao_social = st.text_input("Razão Social", value=dados.get("Razão Social", ""))
        cnpj_val = st.text_input("CNPJ", value=dados.get("CNPJ", ""))
    with col2:
        situacao = st.text_input("Situação", value="ATIVA")
        cpf_master = st.text_input("CPF Master", value=dados.get("CPF Master", ""))
    
    usuario_val = st.text_input("Usuário(s)", value=dados.get("Usuário(s)", ""))

    dados_atualizados = {
        "Razão Social": razao_social,
        "CNPJ": cnpj_val,
        "Situação": "ATIVA",
        "CPF Master": cpf_master,
        "Usuário(s)": usuario_val,
    }

    if st.button("Baixar PDF Pronto", type="primary"):
        if not razao_social.strip() or not cnpj_val.strip():
            st.error("Preencha pelo menos a Razão Social e o CNPJ para gerar o PDF.")
        else:
            caminho_pdf = gerar_pdf(PASTA_SCRIPT, dados_atualizados)
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label="📥 Clique aqui para salvar o PDF",
                    data=f,
                    file_name=os.path.basename(caminho_pdf),
                    mime="application/pdf"
                )
