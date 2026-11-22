// Modelagem inicial de dados - Agendamento de Coletas de Sucata (DECA)
// Apenas classes e atributos. Sem regras de negócio.

#nullable enable
using System;
using System.Collections.Generic;

namespace GrupoQualy.Logistica.Modelos
{
    // ======================= ENUMS =======================

    public enum TipoVeiculo
    {
        RollOn = 1,        // Troca de caçamba (fornecedores menores)
        Garra = 2,         // Pátios maiores, material solto
        CarretaTerceirizada = 3
    }

    public enum TipoMotorista
    {
        Interno = 1,
        Terceirizado = 2
    }

    public enum StatusColeta
    {
        Agendada = 1,
        EmAndamento = 2,
        Concluida = 3,
        Cancelada = 4,
        Urgente = 5
    }

    public enum OrigemSolicitacao
    {
        FornecedorSolicitou = 1,
        LogisticaContatou = 2
    }

    public enum CanalNotificacao
    {
        Sistema = 1,
        Email = 2,
        WhatsApp = 3,
        Telefone = 4
    }

    public enum PerfilUsuario
    {
        Administradora = 1,
        ChefeLogistica = 2,
        Motorista = 3,
        Balanca = 4,
        Financeiro = 5
    }

    // ======================= CADASTROS =======================

    public class Fornecedor
    {
        public int Id { get; set; }
        public string RazaoSocial { get; set; } = string.Empty;
        public string? NomeFantasia { get; set; }
        public string? CnpjCpf { get; set; }
        public string? Telefone { get; set; }
        public string? Email { get; set; }
        public bool Frequente { get; set; }
        public bool Ativo { get; set; }

        public List<PontoColeta> PontosColeta { get; set; } = new();
    }

    public class PontoColeta
    {
        public int Id { get; set; }
        public int FornecedorId { get; set; }
        public string Nome { get; set; } = string.Empty;
        public string Logradouro { get; set; } = string.Empty;
        public string? Numero { get; set; }
        public string Bairro { get; set; } = string.Empty;
        public string Cidade { get; set; } = string.Empty;
        public string Uf { get; set; } = string.Empty;
        public string? Cep { get; set; }
        public double? Latitude { get; set; }
        public double? Longitude { get; set; }
        public string NomeResponsavel { get; set; } = string.Empty;
        public string? ContatoResponsavel { get; set; }
        public TipoVeiculo TipoVeiculoPadrao { get; set; }
        public decimal? PesoGatilhoKg { get; set; }          // Ex.: 2000 kg
        public int? DistanciaPatioKm { get; set; }
        public int? TempoDeslocamentoMinutos { get; set; }   // Ida (pode ser estimado via mapas)
        public string? Observacoes { get; set; }
        public bool Ativo { get; set; }

        public Fornecedor? Fornecedor { get; set; }
    }

    public class Veiculo
    {
        public int Id { get; set; }
        public string Placa { get; set; } = string.Empty;
        public string? Descricao { get; set; }
        public TipoVeiculo Tipo { get; set; }
        public decimal? CapacidadeKg { get; set; }
        public int TempoExecucaoPadraoMinutos { get; set; }  // Garra ~30; Roll-on ~20-25
        public string? IdentificadorRastreador { get; set; }
        public bool Terceirizado { get; set; }
        public bool Ativo { get; set; }

        public int? EmpresaParceiraId { get; set; }
        public EmpresaParceira? EmpresaParceira { get; set; }
    }

    public class EmpresaParceira
    {
        public int Id { get; set; }
        public string RazaoSocial { get; set; } = string.Empty;
        public string? Cnpj { get; set; }
        public string? Telefone { get; set; }
        public string? Email { get; set; }
        public bool Ativo { get; set; }

        public List<Motorista> Motoristas { get; set; } = new();
        public List<Veiculo> Veiculos { get; set; } = new();
    }

    public class Motorista
    {
        public int Id { get; set; }
        public string Nome { get; set; } = string.Empty;
        public string? Cpf { get; set; }
        public string? Cnh { get; set; }
        public string? Telefone { get; set; }
        public string? Email { get; set; }
        public TipoMotorista Tipo { get; set; }
        public bool Ativo { get; set; }

        public int? EmpresaParceiraId { get; set; }
        public EmpresaParceira? EmpresaParceira { get; set; }
        public int? UsuarioId { get; set; }
        public Usuario? Usuario { get; set; }
    }

    public class Usuario
    {
        public int Id { get; set; }
        public string Nome { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public PerfilUsuario Perfil { get; set; }
        public bool Ativo { get; set; }
    }

    // ======================= AGENDAMENTO =======================

    public class DisponibilidadeMotorista
    {
        public int Id { get; set; }
        public int MotoristaId { get; set; }
        public DateTime Inicio { get; set; }
        public DateTime Fim { get; set; }
        public bool Disponivel { get; set; }
        public string? Motivo { get; set; }                  // Folga, férias, manutenção etc.

        public Motorista? Motorista { get; set; }
    }

    public class Coleta
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;

        public int PontoColetaId { get; set; }
        public int? VeiculoId { get; set; }
        public int? MotoristaId { get; set; }
        public int CriadaPorUsuarioId { get; set; }

        public TipoVeiculo TipoVeiculoNecessario { get; set; }
        public OrigemSolicitacao Origem { get; set; }
        public StatusColeta Status { get; set; }
        public string CorStatus { get; set; } = string.Empty; // Ex.: hexadecimal para o painel

        public DateTime DataSolicitacao { get; set; }
        public DateTime DataHoraPrevistaInicio { get; set; }
        public DateTime DataHoraPrevistaFim { get; set; }
        public DateTime? DataHoraRealSaida { get; set; }
        public DateTime? DataHoraRealChegada { get; set; }

        public int TempoDeslocamentoIdaMinutos { get; set; }
        public int TempoDeslocamentoVoltaMinutos { get; set; }
        public int TempoExecucaoMinutos { get; set; }
        public int TempoTotalMinutos { get; set; }           // Ida + volta + execução

        public decimal? PesoEstimadoKg { get; set; }
        public decimal? PesoRealKg { get; set; }
        public bool Urgente { get; set; }
        public int OrdemNaRota { get; set; }
        public string? Observacoes { get; set; }
        public string? MotivoCancelamento { get; set; }

        public string? IdEventoAgendaExterna { get; set; }   // Calendar, se integrado

        public PontoColeta? PontoColeta { get; set; }
        public Veiculo? Veiculo { get; set; }
        public Motorista? Motorista { get; set; }
        public Usuario? CriadaPor { get; set; }
        public TicketDescarregamento? Ticket { get; set; }
        public List<NotificacaoColeta> Notificacoes { get; set; } = new();
        public List<HistoricoStatusColeta> Historico { get; set; } = new();
    }

    public class TicketDescarregamento
    {
        public int Id { get; set; }
        public int ColetaId { get; set; }
        public string Numero { get; set; } = string.Empty;
        public int? PesagemId { get; set; }                  // Vínculo com o módulo da balança
        public decimal? PesoLiquidoKg { get; set; }
        public DateTime? DataHoraDescarregamento { get; set; }

        public Coleta? Coleta { get; set; }
    }

    public class RotaDiaria
    {
        public int Id { get; set; }
        public DateTime Data { get; set; }
        public int VeiculoId { get; set; }
        public int MotoristaId { get; set; }
        public int ElaboradaPorUsuarioId { get; set; }
        public int DistanciaTotalPrevistaKm { get; set; }
        public int TempoTotalPrevistoMinutos { get; set; }
        public DateTime? DataHoraEnvioProgramacao { get; set; }

        public Veiculo? Veiculo { get; set; }
        public Motorista? Motorista { get; set; }
        public Usuario? ElaboradaPor { get; set; }
        public List<Coleta> Coletas { get; set; } = new();
    }

    // ======================= AUDITORIA E COMUNICAÇÃO =======================

    public class HistoricoStatusColeta
    {
        public int Id { get; set; }
        public int ColetaId { get; set; }
        public StatusColeta StatusAnterior { get; set; }
        public StatusColeta StatusNovo { get; set; }
        public DateTime DataHora { get; set; }
        public int UsuarioId { get; set; }
        public string? Observacao { get; set; }

        public Coleta? Coleta { get; set; }
        public Usuario? Usuario { get; set; }
    }

    public class NotificacaoColeta
    {
        public int Id { get; set; }
        public int ColetaId { get; set; }
        public int? MotoristaId { get; set; }
        public int? UsuarioId { get; set; }
        public CanalNotificacao Canal { get; set; }
        public string Mensagem { get; set; } = string.Empty;
        public DateTime DataHoraEnvio { get; set; }
        public bool Lida { get; set; }

        public Coleta? Coleta { get; set; }
    }
}
