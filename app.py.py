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

# FUNÇÃO DE EXTRAÇÃO INTELIGENTE
def extrair_dados_ficha(texto_ficha):
    dados = {
        "Razão Social": "NÃO IDENTIFICADO",
        "CNPJ": "00.000.000/0000-00",
        "Situação": "ATIVA",
        "Capital Social": "",
        "E-mail": "",
        "Agência / Conta": "",
        "CPF Master": "000.000.000-00",
        "Nome Sócio": "",
        "Renda": "",
        "Data de Nascimento": "",
        "Usuário(s)": "",
        "Telefone GOV": "",
    }

    if not texto_ficha.strip():
        return dados

    texto_ficha = texto_ficha.replace("\\", "/")

    # ---------- FORMATO NOVO (Empresa / Capital social / Sócios) ----------
    match_empresa = re.search(r"Empresa[:\s]+([^\n]+)", texto_ficha, re.IGNORECASE)
    if match_empresa:
        dados["Razão Social"] = match_empresa.group(1).strip()

    match_capital = re.search(r"Capital social[:\s]*R?\$?\s*([\d.,]+)", texto_ficha, re.IGNORECASE)
    if match_capital:
        dados["Capital Social"] = f"R$ {match_capital.group(1).strip()}"

    match_situacao = re.search(r"Situa[çc][ãa]o cadastral[:\s]+([^\n]+)", texto_ficha, re.IGNORECASE)
    if match_situacao:
        dados["Situação"] = match_situacao.group(1).strip()

    match_email = re.search(r"E-?mail[:\s]+([^\n]+)", texto_ficha, re.IGNORECASE)
    if match_email:
        dados["E-mail"] = match_email.group(1).strip()

    match_agencia = re.search(r"Ag[êe]ncia[:\s]*(\d+)\s*/\s*Conta[:\s]*([\d-]+)", texto_ficha, re.IGNORECASE)
    if match_agencia:
        dados["Agência / Conta"] = f"{match_agencia.group(1).strip()} / {match_agencia.group(2).strip()}"

    # Sócio completo (mesma linha com | )
    match_socio = re.search(
        r"CPF[:\s]*(\d{11})\s*\|\s*Nome[:\s]*([^|]+?)\s*\|\s*Renda[:\s]*R?\$?\s*([\d.,]+)\s*\|\s*Data de nascimento[:\s]*(\d{2}/\d{2}/\d{4})",
        texto_ficha,
        re.IGNORECASE,
    )
    if match_socio:
        cpf = match_socio.group(1)
        dados["CPF Master"] = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        dados["Nome Sócio"] = match_socio.group(2).strip()
        dados["Renda"] = f"R$ {match_socio.group(3).strip()}"
        dados["Data de Nascimento"] = match_socio.group(4).strip()

    match_usuario = re.search(r"Usu[áa]rio[:\s]+([A-Za-z0-9]+)", texto_ficha, re.IGNORECASE)
    if match_usuario:
        dados["Usuário(s)"] = match_usuario.group(1).strip()

    match_tel = re.search(r"Telefone GOV[:\s]*(\d{10,11})", texto_ficha, re.IGNORECASE)
    if match_tel:
        dados["Telefone GOV"] = match_tel.group(1).strip()

    # ---------- FORMATOS ANTIGOS (compatibilidade) ----------
    match_cnpj_rotulo = re.search(r"CNPJ[:\s]+([\d./-]+)", texto_ficha, re.IGNORECASE)
    if match_cnpj_rotulo:
        c_limpo = re.sub(r"\D", "", match_cnpj_rotulo.group(1))
        if len(c_limpo) == 14:
            dados["CNPJ"] = f"{c_limpo[:2]}.{c_limpo[2:5]}.{c_limpo[5:8]}/{c_limpo[8:12]}-{c_limpo[12:]}"

    if dados["Razão Social"] == "NÃO IDENTIFICADO":
        match_razao_rotulo = re.search(r"RAZ[ÃA]O SOCIAL[:\s]+([^\n]+)", texto_ficha, re.IGNORECASE)
        if match_razao_rotulo:
            dados["Razão Social"] = match_razao_rotulo.group(1).strip()

    match_cpf_rotulo = re.search(r"CPF USU[ÁA]RIO MASTER[:\s]+([\d.-]+)", texto_ficha, re.IGNORECASE)
    if match_cpf_rotulo and dados["CPF Master"] == "000.000.000-00":
        cpf_limpo = re.sub(r"\D", "", match_cpf_rotulo.group(1))
        if len(cpf_limpo) == 11:
            dados["CPF Master"] = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"

    if not dados["Usuário(s)"]:
        matches_user = re.findall(r"USU[ÁA]RIOS?[:\s]+([A-Za-z0-9]+)", texto_ficha, re.IGNORECASE)
        for val_user in matches_user:
            val_user_limpo = val_user.strip()
            if val_user_limpo and val_user_limpo.upper() != "MASTER":
                dados["Usuário(s)"] = val_user_limpo
                break

    if dados["CNPJ"] == "00.000.000/0000-00":
        match_cnpj = re.search(r"\[(\d{14})\]", texto_ficha)
        if not match_cnpj:
            match_cnpj = re.search(r"\b(\d{14})\b", texto_ficha)
        if match_cnpj:
            c = match_cnpj.group(1)
            dados["CNPJ"] = f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

    if dados["Razão Social"] == "NÃO IDENTIFICADO":
        match_razao = re.search(r"\[\d+\|\d+-[0-9X]\]\s*-\s*\[\d+\]\s*-\s*\[([^\]]+)\]", texto_ficha)
        if match_razao:
            dados["Razão Social"] = match_razao.group(1).strip()
        else:
            match_nome = re.search(r"Nome:\s*([^|]+)", texto_ficha, re.IGNORECASE)
            if match_nome:
                dados["Razão Social"] = match_nome.group(1).strip()

    if dados["CPF Master"] == "000.000.000-00":
        match_cpf = re.search(r"CPF:\s*(\d{11})", texto_ficha, re.IGNORECASE)
        if match_cpf:
            cpf = match_cpf.group(1)
            dados["CPF Master"] = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

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
        if v is not None and str(v).strip():
            tabela.append([Paragraph(f"<b>{k}:</b>", estilo_texto), Paragraph(str(v), estilo_texto)])

    t = Table(tabela, colWidths=[135, 350])
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
    "Capital Social": "",
    "E-mail": "",
    "Agência / Conta": "",
    "CPF Master": "",
    "Nome Sócio": "",
    "Renda": "",
    "Data de Nascimento": "",
    "Usuário(s)": "",
    "Telefone GOV": "",
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
        capital_val = st.text_input("Capital Social", value=dados.get("Capital Social", ""))
        email_val = st.text_input("E-mail", value=dados.get("E-mail", ""))
        agencia_val = st.text_input("Agência / Conta", value=dados.get("Agência / Conta", ""))
    with col2:
        situacao = st.text_input("Situação", value=dados.get("Situação", "ATIVA"))
        cpf_master = st.text_input("CPF Master", value=dados.get("CPF Master", ""))
        nome_socio = st.text_input("Nome Sócio", value=dados.get("Nome Sócio", ""))
        renda_val = st.text_input("Renda", value=dados.get("Renda", ""))
        nascimento_val = st.text_input("Data de Nascimento", value=dados.get("Data de Nascimento", ""))
    
    col_u1, col_u2 = st.columns([2, 2])
    with col_u1:
        usuario_val = st.text_input("Usuário(s)", value=dados.get("Usuário(s)", ""))
        telefone_val = st.text_input("Telefone GOV", value=dados.get("Telefone GOV", ""))
    with col_u2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Alinhamento vertical
        incluir_usuario = st.checkbox("Incluir Usuário no PDF", value=True)
        incluir_socio = st.checkbox("Incluir Sócio/Renda/Nascimento no PDF", value=True)

    dados_atualizados = {
        "Razão Social": razao_social,
        "CNPJ": cnpj_val,
        "Situação": situacao,
    }
    if capital_val.strip():
        dados_atualizados["Capital Social"] = capital_val
    if email_val.strip():
        dados_atualizados["E-mail"] = email_val
    if agencia_val.strip():
        dados_atualizados["Agência / Conta"] = agencia_val
    if incluir_socio:
        if cpf_master.strip():
            dados_atualizados["CPF Master"] = cpf_master
        if nome_socio.strip():
            dados_atualizados["Nome Sócio"] = nome_socio
        if renda_val.strip():
            dados_atualizados["Renda"] = renda_val
        if nascimento_val.strip():
            dados_atualizados["Data de Nascimento"] = nascimento_val
    if incluir_usuario and usuario_val.strip():
        dados_atualizados["Usuário(s)"] = usuario_val
    if telefone_val.strip():
        dados_atualizados["Telefone GOV"] = telefone_val

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
