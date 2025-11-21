# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func, delete, select, update
from sqlalchemy.exc import IntegrityError 
import random
import os
from sqlalchemy import func, extract


# 💡 Documentação: Inicialização
app = Flask(__name__)

# ----------------------------------------------------
# 📌 CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# ----------------------------------------------------
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Render usa 'postgres://', mas o SQLAlchemy espera 'postgresql://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("Usando PostgreSQL (Produção)")
else:
    # Versão local (SQLite)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///padaria.db'
    print("Usando SQLite (Desenvolvimento Local)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------------------------------------------
# 📌 MODELOS DO BANCO DE DADOS (Tabelas)
# ----------------------------------------------------

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    nome = db.Column(db.String(80), nullable=False, unique=True)
    valor = db.Column(db.Float, nullable=False)
    codigo_barra = db.Column(db.String(50), unique=True, nullable=False)
    data_fabricacao = db.Column(db.String(10), nullable=False)
    
    def __repr__(self):
        return f'<Produto {self.nome}>'

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False) 
    password = db.Column(db.String(120), nullable=False) 
    nome = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(50), nullable=False) 

    def __repr__(self):
        return f'<Funcionario {self.username}>'

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    contato_wpp = db.Column(db.String(20))
    email = db.Column(db.String(100))
    status_credito = db.Column(db.String(20), default='Pendente', nullable=False) 

    def __repr__(self):
        return f'<Cliente {self.nome}>'
    
class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True) 
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    data_venda = db.Column(db.DateTime, nullable=False, default=datetime.now)
    total_venda = db.Column(db.Float, nullable=False, default=0.0)
    valor_desconto = db.Column(db.Float, nullable=False, default=0.0) 
    
    # AJUSTE 1: Novo campo para armazenar a forma de pagamento
    forma_pagamento = db.Column(db.String(50), nullable=False, default='Dinheiro') # <--- NOVO CAMPO
    
    itens = db.relationship('VendaProduto', backref='venda', lazy=True, cascade="all, delete-orphan")
    cliente = db.relationship('Cliente', backref='vendas')
    
    def __repr__(self):
        return f'<Venda {self.id}>'

class VendaProduto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    
    produto = db.relationship('Produto')

    def __repr__(self):
        return f'<ItemVenda Venda:{self.venda_id} Produto:{self.produto_id}>'

# ----------------------------------------------------
# 📌 FUNÇÕES AUXILIARES E FILTROS JINJA2
# ----------------------------------------------------

@app.template_filter()
def formatar_moeda(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def check_login():
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar o sistema.', 'error')
        return redirect(url_for('login'))
    return None # Retorna None se estiver logado



#Condição: O último dígito é ímpar (ultimo_digito % 2 != 0).
#Lógica: O sistema gera um número aleatório entre 0.0 e 1.0 (random.random()).
#Se o número aleatório for menor que 0.7 (ou seja, 70% de chance), o resultado é 'Aprovado'.
#Caso contrário (30% de chance), o resultado é 'Negado'.
#Este grupo tem alta chance (70%) de ser aprovado.
#------------------------------------------------------------------------------
#Condição: O último dígito é par (ou 0).
#Lógica: Novamente, gera um número aleatório entre 0.0 e 1.0.
#Se o número aleatório for menor que 0.3 (ou seja, 30% de chance), o resultado é 'Aprovado'.
#Caso contrário (70% de chance), o resultado é 'Negado'.
#Este grupo tem baixa chance (30%) de ser aprovado.
#random:Gera um número de ponto flutuante (decimal).

def consultar_serasa(cpf):
    """Simula a consulta ao Serasa."""
    try:
        ultimo_digito = int(cpf[-1])
    except:
        ultimo_digito = 0 

    if ultimo_digito % 2 != 0:
        if random.random() < 0.7:
            return 'Aprovado'
        else:
            return 'Negado'
    else:
        if random.random() < 0.3:
            return 'Aprovado'
        else:
            return 'Negado'

# ----------------------------------------------------
# 📌 ROTAS PRINCIPAIS (Login, Logout, Dashboard)
# ----------------------------------------------------

@app.route('/')
def index():
    return check_login() or redirect(url_for('dashboard')) 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.session.execute(
            select(Funcionario).filter_by(username=username)
        ).scalar_one_or_none()
        
        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            session['nome_usuario'] = user.nome
            flash(f'Bem-vindo, {user.nome}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return check_login() or render_template('dashboard.html', 
                                            padaria_nome="Pão FresQUIM", 
                                            usuario_logado=session['nome_usuario'])

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('nome_usuario', None)
    flash('Sessão encerrada com sucesso.', 'success')
    return redirect(url_for('login'))


# ----------------------------------------------------
# 📌 ROTAS DE VENDAS (Ajustadas com Desconto e Exclusão)
# ----------------------------------------------------

@app.route('/menu/vendas')
def menu_vendas():
    return check_login() or render_template('menu_vendas.html')

@app.route('/registrar/venda', methods=['GET', 'POST'])
def registrar_venda():
    if not check_login() is None:
        return check_login()

    if request.method == 'POST':
        cliente_id_str = request.form.get('cliente_id')
        cliente_id = int(cliente_id_str) if cliente_id_str else None
        
        produto_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        
        valor_desconto_str = request.form.get('desconto_final', '0.0')
        try:
            valor_desconto = abs(float(valor_desconto_str.replace(',', '.')))
        except ValueError:
            valor_desconto = 0.0
        forma_pagamento = request.form.get('forma_pagamento', 'Dinheiro') 
        itens_venda = []
        subtotal = 0.0 

        try:
            for produto_id_str, quantidade_str in zip(produto_ids, quantidades):
                if not produto_id_str or not quantidade_str:
                    continue
                
                produto_id = int(produto_id_str)
                quantidade = int(quantidade_str)

                produto = db.get_or_404(Produto, produto_id)
                preco_unitario = produto.valor
                
                if quantidade <= 0:
                    continue

                subtotal += preco_unitario * quantidade
                
                itens_venda.append(VendaProduto(
                    produto_id=produto_id,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario
                    
                ))

            if not itens_venda:
                flash('Nenhum item válido foi adicionado à venda.', 'error')
                return redirect(url_for('registrar_venda'))
                
            total_venda_final = max(0.0, subtotal - valor_desconto)

            nova_venda = Venda(
                cliente_id=cliente_id,
                funcionario_id=session['user_id'],
                total_venda=total_venda_final,
                valor_desconto=valor_desconto,
                forma_pagamento=forma_pagamento
            )
            
            db.session.add(nova_venda)
            db.session.flush() 
            
            for item in itens_venda:
                item.venda_id = nova_venda.id
                db.session.add(item)
            
            db.session.commit()
            
            flash(f'Venda #{nova_venda.id} de {formatar_moeda(nova_venda.total_venda)} registrada com sucesso!', 'success')
            return redirect(url_for('lista_vendas'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar a venda: {str(e)}', 'error')
            return redirect(url_for('registrar_venda'))

    # Rota GET: Serialização JSON
    produtos_query = db.session.execute(select(Produto)).scalars().all()
    produtos_serializados = [{
        'id': p.id, 'nome': p.nome, 'valor': p.valor 
    } for p in produtos_query]
    
    clientes_query = db.session.execute(select(Cliente)).scalars().all()
    
    # 💡 CORREÇÃO: Serializa os objetos Cliente para que sejam JSON serializáveis
    clientes_serializados = [{
        'id': c.id, 
        'nome': c.nome, 
        'cpf': c.cpf, 
        'status_credito': c.status_credito
    } for c in clientes_query]
    
    return render_template(
        'registrar_venda.html', 
        produtos=produtos_serializados,
        clientes=clientes_serializados, 
    )

@app.route('/lista/vendas', methods=['GET'])
def lista_vendas():
    if not check_login() is None:
        return check_login()
        
    vendas = db.session.execute(
        select(Venda).order_by(Venda.data_venda.desc())
    ).scalars().all()
    
    return render_template('lista_vendas.html', vendas=vendas)

@app.route('/excluir/venda/<int:venda_id>', methods=['POST'])
def excluir_venda(venda_id):
    if not check_login() is None:
        return check_login()
        
    try:
        venda = db.get_or_404(Venda, venda_id)
        
        # Excluir os itens de venda relacionados
        db.session.execute(
            delete(VendaProduto).where(VendaProduto.venda_id == venda_id)
        )
        
        db.session.delete(venda)
        db.session.commit()
        
        flash(f'Venda #{venda_id} excluída com sucesso.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a venda #{venda_id}. Detalhe: {str(e)}', 'error')
        
    return redirect(url_for('lista_vendas')) 

@app.route('/relatorio/vendas/periodo', methods=['GET', 'POST'])
def relatorio_vendas_periodo():
    if not check_login() is None:
        return check_login()

    vendas = []
    data_inicio = request.form.get('data_inicio')
    data_fim = request.form.get('data_fim')
    total_periodo = 0.0

    if request.method == 'POST' and data_inicio and data_fim:
        try:
            # 1. Converte as strings de data para objetos datetime para consulta
            start_date = datetime.strptime(data_inicio, '%Y-%m-%d')
            # Inclui o dia de término inteiro (adicionando 23:59:59)
            end_date = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

            # 2. Consulta de Vendas (filtrada e ordenada)
            vendas_query = db.session.execute(
                select(Venda)
                .filter(Venda.data_venda.between(start_date, end_date))
                .order_by(Venda.data_venda.desc())
            ).scalars().all()
            
            vendas = vendas_query
            
            # 3. Cálculo do Total (usando func.sum do SQLAlchemy para performance)
            total_result = db.session.execute(
                select(func.sum(Venda.total_venda))
                .filter(Venda.data_venda.between(start_date, end_date))
            ).scalar_one_or_none()

            total_periodo = total_result if total_result else 0.0
            
            flash(f"Relatório de Vendas gerado de {data_inicio} até {data_fim}.", 'success')

        except ValueError:
            flash("Formato de data inválido. Use AAAA-MM-DD.", 'error')
        except Exception as e:
            flash(f"Erro ao gerar relatório: {str(e)}", 'error')

    return render_template(
        'relatorio_vendas_periodo.html',
        vendas=vendas,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_periodo=total_periodo
    )

@app.route('/relatorio/vendas/produto')
def relatorio_vendas_produto():
    if not check_login() is None:
        return check_login()
    
    # Esta rota apenas renderiza o template que contém o formulário de filtro
    return render_template('relatorio_vendas_produto.html')

# Rota API: Fornece os dados JSON com filtro de período
@app.route('/api/vendas/produto_data')
def api_vendas_produto_data():
    if not check_login() is None:
        return jsonify({'error': 'Não Autorizado'}), 401 
        
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    
    # 1. Base da consulta (Agrupamento por Produto)
    stmt = select(
        Produto.nome,
        # Soma o valor total faturado (quantidade * valor unitário na venda)
        func.sum(VendaProduto.quantidade * VendaProduto.preco_unitario).label('total_vendido')
    ).join(Produto, VendaProduto.produto_id == Produto.id)

    # 2. Adiciona o filtro de período, se as datas existirem
    if data_inicio_str and data_fim_str:
        try:
            # Converte as strings de data (espera-se YYYY-MM-DD do HTML)
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            
            # CORREÇÃO: Formato '%Y-%m-%d' correto
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

            # Faz o JOIN com Venda para filtrar pela data da venda
            stmt = stmt.join(Venda, VendaProduto.venda_id == Venda.id).where(
                Venda.data_venda.between(data_inicio, data_fim)
            )

        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use AAAA-MM-DD.'}), 400
        except Exception as e:
            print(f"Erro no filtro de data (JOIN/Modelos): {e}")
            return jsonify({'error': 'Erro interno ao processar datas.'}), 500

    # 3. Agrupamento final e Ordenação
    stmt = stmt.group_by(Produto.nome).order_by(func.sum(VendaProduto.quantidade * VendaProduto.preco_unitario).desc())

    try:
        dados_agregados = db.session.execute(stmt).all()
        
        labels = [d[0] for d in dados_agregados]
        data = [float(d[1]) for d in dados_agregados]
        
        return jsonify({'labels': labels, 'data': data})

    except Exception as e:
        print(f"Erro ao gerar dados do gráfico: {e}")
        return jsonify({'error': str(e)}), 500
    


    

# ----------------------------------------------------
# 📌 ROTAS DE PRODUTOS
# ----------------------------------------------------

@app.route('/menu/produtos')
def menu_produtos():
    return check_login() or render_template('menu_produtos.html')

@app.route('/lista/produtos', methods=['GET'])
def lista_produtos():
    if not check_login() is None:
        return check_login()
        
    produtos = db.session.execute(select(Produto).order_by(Produto.nome)).scalars().all()
    return render_template('lista_produtos.html', produtos=produtos)

@app.route('/cadastro/produto', methods=['GET', 'POST'])
def cadastro_produto():
    if not check_login() is None:
        return check_login()

    if request.method == 'POST':
        try:
            novo_produto = Produto(
                nome=request.form['nome'],
                valor=float(request.form['valor'].replace(',', '.')),
                codigo_barra=request.form['codigo_barra'],
                data_fabricacao=request.form['data_fabricacao']
            )
            db.session.add(novo_produto)
            db.session.commit()
            flash('Produto cadastrado com sucesso!', 'success')
            return redirect(url_for('lista_produtos'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Nome ou Código de Barras já existem.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar produto: {str(e)}', 'error')

    return render_template('cadastro_produto.html')

@app.route('/editar/produto/<int:produto_id>', methods=['GET', 'POST'])
def editar_produto(produto_id):
    if not check_login() is None:
        return check_login()
    
    produto = db.get_or_404(Produto, produto_id)

    if request.method == 'POST':
        try:
            produto.nome = request.form['nome']
            produto.valor = float(request.form['valor'].replace(',', '.'))
            produto.codigo_barra = request.form['codigo_barra']
            produto.data_fabricacao = request.form['data_fabricacao']
            db.session.commit()
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('lista_produtos'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Nome ou Código de Barras já existem.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar produto: {str(e)}', 'error')

    return render_template('editar_produto.html', produto=produto)

@app.route('/excluir/produto/<int:produto_id>', methods=['POST'])
def excluir_produto(produto_id):
    if not check_login() is None:
        return check_login()
    
    produto = db.get_or_404(Produto, produto_id)
    try:
        db.session.delete(produto)
        db.session.commit()
        flash('Produto excluído com sucesso.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Erro: Este produto está ligado a vendas existentes e não pode ser excluído.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir produto: {str(e)}', 'error')
        
    return redirect(url_for('lista_produtos'))


# ----------------------------------------------------
# 📌 ROTAS DE CLIENTES
# ----------------------------------------------------

@app.route('/menu/clientes')
def menu_clientes():
    return check_login() or render_template('menu_clientes.html')

@app.route('/lista/clientes', methods=['GET'])
def lista_clientes():
    if not check_login() is None:
        return check_login()
        
    clientes = db.session.execute(select(Cliente).order_by(Cliente.nome)).scalars().all()
    return render_template('lista_clientes.html', clientes=clientes)

@app.route('/cadastro/cliente', methods=['GET', 'POST'])
def cadastro_cliente():
    if not check_login() is None:
        return check_login()

    if request.method == 'POST':
        try:
            cpf = request.form['cpf'].strip().replace('.', '').replace('-', '')
            novo_cliente = Cliente(
                nome=request.form['nome'],
                cpf=cpf,
                contato_wpp=request.form['contato_wpp'],
                email=request.form['email'],
                status_credito='Pendente' # Inicia como pendente
            )
            db.session.add(novo_cliente)
            db.session.commit()
            
            # Consulta Serasa simulada após o cadastro
            novo_cliente.status_credito = consultar_serasa(novo_cliente.cpf)
            db.session.commit() 
            
            flash('Cliente cadastrado com sucesso e status de crédito verificado!', 'success')
            return redirect(url_for('lista_clientes'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: CPF já existe na base de dados.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar cliente: {str(e)}', 'error')

    return render_template('cadastro_cliente.html')


@app.route('/excluir/cliente/<int:cliente_id>', methods=['POST'])
def excluir_cliente(cliente_id):
    if not check_login() is None:
        return check_login()
    
    cliente = db.get_or_404(Cliente, cliente_id)
    try:
        db.session.delete(cliente)
        db.session.commit()
        flash('Cliente excluído com sucesso.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Erro: Este cliente está ligado a vendas existentes e não pode ser excluído.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir cliente: {str(e)}', 'error')

    return redirect(url_for('lista_clientes'))

@app.route('/editar/cliente/<int:cliente_id>', methods=['GET', 'POST'])
def editar_cliente(cliente_id):
    if not check_login() is None:
        return check_login()

    cliente = db.get_or_404(Cliente, cliente_id)

    if request.method == 'POST':
        try:
            # Note: O CPF é readonly no template, então não o alteramos via POST
            cliente.nome = request.form['nome']
            cliente.contato_wpp = request.form['contato_wpp']
            cliente.email = request.form['email']
            # Permite alterar manualmente o status de crédito (como está no seu editar_cliente.html)
            cliente.status_credito = request.form['status_credito'] 

            db.session.commit()
            flash('Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('lista_clientes'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um registro com este CPF ou e-mail.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar cliente: {str(e)}', 'error')

    return render_template('editar_cliente.html', cliente=cliente)

# ----------------------------------------------------
# 📌 ROTAS DE FUNCIONÁRIOS
# ----------------------------------------------------

@app.route('/menu/funcionarios')
def menu_funcionarios():
    return check_login() or render_template('menu_funcionarios.html')


@app.route('/lista/funcionarios', methods=['GET'])
def lista_funcionarios():
    if not check_login() is None:
        return check_login()
    
    funcionarios = db.session.execute(select(Funcionario).order_by(Funcionario.nome)).scalars().all()
    return render_template('lista_funcionarios.html', funcionarios=funcionarios)

@app.route('/cadastro/funcionario', methods=['GET', 'POST'])
def cadastro_funcionario():
    if not check_login() is None:
        return check_login()

    if request.method == 'POST':
        try:
            novo_funcionario = Funcionario(
                username=request.form['username'],
                password=request.form['password'],
                nome=request.form['nome'],
                cargo=request.form['cargo']
            )
            db.session.add(novo_funcionario)
            db.session.commit()
            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('menu_funcionarios'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Usuário (username) já existe.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar funcionário: {str(e)}', 'error')

    return render_template('cadastro_funcionario.html')

@app.route('/excluir/funcionario/<int:funcionario_id>', methods=['POST'])
def excluir_funcionario(funcionario_id):
    if not check_login() is None:
        return check_login()
    
    funcionario = db.get_or_404(Funcionario, funcionario_id)
    
    # Previne que o próprio usuário logado se exclua
    if funcionario.id == session['user_id']:
        flash('Você não pode excluir sua própria conta enquanto estiver logado.', 'error')
        return redirect(url_for('lista_funcionarios'))

    try:
        db.session.delete(funcionario)
        db.session.commit()
        flash('Funcionário excluído com sucesso.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Erro: Este funcionário está ligado a vendas existentes e não pode ser excluído.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir funcionário: {str(e)}', 'error')
        
    return redirect(url_for('lista_funcionarios'))

@app.route('/editar/funcionario/<int:funcionario_id>', methods=['GET', 'POST'])
def editar_funcionario(funcionario_id):
    if not check_login() is None:
        return check_login()
    
    funcionario = db.get_or_404(Funcionario, funcionario_id)

    if request.method == 'POST':
        try:
            funcionario.nome = request.form['nome']
            funcionario.cargo = request.form['cargo']
            
            # Atualiza a senha apenas se um novo valor for fornecido
            nova_senha = request.form.get('password')
            if nova_senha:
                funcionario.password = nova_senha 
                
            # O username é readonly no template, não deve ser alterado aqui

            db.session.commit()
            flash('Funcionário atualizado com sucesso!', 'success')
            return redirect(url_for('lista_funcionarios'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Nome de usuário já existe. O username não pode ser alterado.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar funcionário: {str(e)}', 'error')

    return render_template('editar_funcionario.html', funcionario=funcionario)

# ----------------------------------------------------
# 📌 ROTAS CAMERAS
# ----------------------------------------------------



@app.route('/menu/cameras')
def menu_cameras():
   return check_login() or render_template('menu_cameras.html')


@app.route('/menu/camera_balcao')
def camera_balcao():
    # Rota para a câmera do balcão
    return check_login() or render_template('camera_balcao.html')


@app.route('/menu/camera_cozinha')
def camera_cozinha():
    # CORRIGIDO: Nome da função de rota coerente com o template 'camera_cozinha.html'
    return check_login() or render_template('camera_cozinha.html')


@app.route('/menu/relatorios')
def menu_relatorios():
    return check_login() or render_template('menu_relatorios.html')

# ----------------------------------------------------
# 🚀 EXECUÇÃO DO APLICATIVO
# ----------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        # Cria o banco de dados e as tabelas
        db.create_all() 
        
        # Cria usuário admin se não existir
        admin_exists = db.session.execute(
            select(Funcionario).filter_by(username='admin')
        ).scalar_one_or_none()
        
        if admin_exists is None:
            admin = Funcionario(username='admin', password='123', nome='Sr. Joaquim', cargo='Gerente')
            db.session.add(admin)
            db.session.commit()
            print(">>> Usuário padrão 'admin' criado. Senha: 123 <<<")
            
    app.run(debug=True)