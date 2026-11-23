/**
 * Gráficos Futuristas Translúcidos — Grupo Qualy (Chart.js 4)
 * Paleta Eco-Verde Qualy + Glassmorphism + Interatividade + Sync Modo Claro/Escuro
 */
(function () {
  if (typeof Chart === "undefined") return;

  // Plugin customizado de brilho neon sutil nos traços e barras
  const qualyNeonGlowPlugin = {
    id: "qualyNeonGlow",
    beforeDatasetDraw(chart, args) {
      const opts = chart.options?.plugins?.qualyNeonGlow;
      if (!opts || opts.enabled === false) return;
      const ctx = chart.ctx;
      ctx.save();
      const ds = chart.data.datasets[args.index] || {};
      ctx.shadowColor = ds._glowColor || opts.color || "rgba(57, 211, 83, 0.48)";
      ctx.shadowBlur = opts.blur ?? 14;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 2;
    },
    afterDatasetDraw(chart) {
      const opts = chart.options?.plugins?.qualyNeonGlow;
      if (!opts || opts.enabled === false) return;
      chart.ctx.restore();
    },
  };

  Chart.register(qualyNeonGlowPlugin);

  function isDark() {
    return document.documentElement.getAttribute("data-theme") === "dark";
  }

  function themePalette() {
    const dark = isDark();
    return {
      dark,
      text: dark ? "#e2ecf4" : "#1e3a29",
      muted: dark ? "#94a3b8" : "#526275",
      grid: dark ? "rgba(74, 222, 128, 0.12)" : "rgba(47, 168, 54, 0.10)",
      tooltipBg: dark ? "rgba(15, 23, 34, 0.94)" : "rgba(255, 255, 255, 0.95)",
      tooltipTitle: dark ? "#4ade80" : "#143d25",
      tooltipBody: dark ? "#eef3f8" : "#0f172a",
      tooltipBorder: dark ? "rgba(74, 222, 128, 0.48)" : "rgba(47, 168, 54, 0.38)",
      neonGreen: dark ? "#4ade80" : "#2fa836",
      emerald: dark ? "#10e09b" : "#10b981",
      cyan: dark ? "#2dd4bf" : "#0891b2",
      steel: dark ? "#38bdf8" : "#1f5e8c",
      amber: dark ? "#fbbf24" : "#d97706",
      slate: dark ? "#64748b" : "#64748b",
      glowBlur: dark ? 15 : 8,
    };
  }

  function makeVerticalGradient(ctx, chartArea, topColor, bottomColor) {
    if (!chartArea) return topColor;
    const grad = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    grad.addColorStop(0, topColor);
    grad.addColorStop(1, bottomColor);
    return grad;
  }

  function makeHorizontalGradient(ctx, chartArea, leftColor, rightColor) {
    if (!chartArea) return rightColor;
    const grad = ctx.createLinearGradient(chartArea.left, 0, chartArea.right, 0);
    grad.addColorStop(0, leftColor);
    grad.addColorStop(1, rightColor);
    return grad;
  }

  function fmtKg(val) {
    return (
      Number(val || 0).toLocaleString("pt-BR", {
        maximumFractionDigits: 1,
      }) + " kg"
    );
  }

  function baseTooltip(pal) {
    return {
      backgroundColor: pal.tooltipBg,
      titleColor: pal.tooltipTitle,
      bodyColor: pal.tooltipBody,
      borderColor: pal.tooltipBorder,
      borderWidth: 1,
      padding: 12,
      cornerRadius: 12,
      displayColors: true,
      boxPadding: 5,
      titleFont: { family: "Space Grotesk, Inter, sans-serif", size: 13, weight: "700" },
      bodyFont: { family: "Inter, sans-serif", size: 12, weight: "500" },
    };
  }

  // Gera conjunto de demonstração quando o período ainda não possui coletas
  function gerarDadosSimulados(seriesReais) {
    const baseDias = (seriesReais.evolucao_diaria || []).slice(-14);
    const labels = baseDias.length
      ? baseDias.map((d) => d.label)
      : ["01/11", "02/11", "03/11", "04/11", "05/11", "06/11", "07/11", "08/11", "09/11", "10/11"];
    const pesos = [4200, 6800, 5400, 9100, 7600, 11200, 8450, 10300, 6900, 12400, 9800, 11500, 8900, 13200];
    const qtds = [2, 4, 3, 5, 4, 6, 5, 6, 4, 7, 5, 6, 5, 7];

    return {
      ...seriesReais,
      simulado: true,
      has_data: true,
      evolucao_diaria: labels.map((lbl, idx) => ({
        data: baseDias[idx]?.data || lbl,
        label: lbl,
        total_coletas: qtds[idx % qtds.length],
        concluidas: Math.max(qtds[idx % qtds.length] - 1, 1),
        kg_transportados: pesos[idx % pesos.length],
      })),
      por_status: {
        chaves: ["concluida", "em_andamento", "agendada", "cancelada"],
        labels: ["Concluídas", "Em andamento", "Agendadas", "Canceladas"],
        valores: [34, 7, 11, 3],
      },
      por_bairro: [
        { bairro: "Distrito Industrial", total_coletas: 14, kg_total: 36400 },
        { bairro: "Centro", total_coletas: 11, kg_total: 24800 },
        { bairro: "Vila Galvão", total_coletas: 9, kg_total: 19200 },
        { bairro: "Jardim Satélite", total_coletas: 7, kg_total: 14600 },
        { bairro: "Parque Tecnológico", total_coletas: 5, kg_total: 11300 },
      ],
      por_veiculo:
        seriesReais.por_veiculo && seriesReais.por_veiculo.length
          ? seriesReais.por_veiculo.map((v, i) => ({
              ...v,
              total_coletas: [18, 15, 13, 9][i % 4],
              kg_total: [44200, 38600, 29400, 19800][i % 4],
            }))
          : [
              { placa: "QAL1A01", tipo_label: "Roll-on", total_coletas: 18, kg_total: 44200 },
              { placa: "QAL1A02", tipo_label: "Garra 1", total_coletas: 15, kg_total: 38600 },
              { placa: "QAL1A03", tipo_label: "Garra 2", total_coletas: 13, kg_total: 29400 },
            ],
    };
  }

  // =========================================================================
  // Dashboard Completo de Indicadores (/relatorios/)
  // =========================================================================
  window.initIndicadoresCharts = function (seriesReais) {
    const state = {
      realData: seriesReais,
      useSim: false,
      evolucaoMode: "ambos", // 'kg' | 'coletas' | 'ambos'
      bairroMode: "kg", // 'kg' | 'coletas'
      frotaMode: "kg", // 'kg' | 'coletas'
      charts: {},
    };

    function activeData() {
      return state.useSim ? gerarDadosSimulados(state.realData) : state.realData;
    }

    function destroyAll() {
      Object.keys(state.charts).forEach((k) => {
        if (state.charts[k]) {
          state.charts[k].destroy();
          delete state.charts[k];
        }
      });
    }

    function renderEvolucao(data, pal) {
      const canvas = document.getElementById("chart-evolucao");
      if (!canvas) return;
      const ev = data.evolucao_diaria || [];
      const labels = ev.map((d) => d.label);
      const kgVals = ev.map((d) => d.kg_transportados);
      const colVals = ev.map((d) => d.total_coletas);

      const datasets = [];
      if (state.evolucaoMode === "kg" || state.evolucaoMode === "ambos") {
        datasets.push({
          type: "line",
          label: "Volume Reciclado (kg)",
          data: kgVals,
          yAxisID: "y",
          tension: 0.42,
          fill: true,
          borderWidth: 2.6,
          borderColor: pal.neonGreen,
          _glowColor: pal.dark ? "rgba(78, 255, 117, 0.55)" : "rgba(47, 168, 54, 0.36)",
          pointRadius: ev.length > 20 ? 2.5 : 4,
          pointHoverRadius: 7,
          pointBackgroundColor: pal.neonGreen,
          pointBorderColor: pal.dark ? "#05140b" : "#ffffff",
          pointBorderWidth: 2,
          backgroundColor: (ctx) =>
            makeVerticalGradient(
              ctx.chart.ctx,
              ctx.chart.chartArea,
              pal.dark ? "rgba(57, 211, 83, 0.42)" : "rgba(47, 168, 54, 0.30)",
              "rgba(16, 185, 129, 0.01)"
            ),
        });
      }

      if (state.evolucaoMode === "coletas" || state.evolucaoMode === "ambos") {
        datasets.push({
          type: "bar",
          label: "Qtd. Coletas",
          data: colVals,
          yAxisID: state.evolucaoMode === "ambos" ? "y1" : "y",
          borderRadius: 8,
          maxBarThickness: 26,
          borderWidth: 1.4,
          borderColor: pal.cyan,
          _glowColor: pal.dark ? "rgba(0, 229, 190, 0.42)" : "rgba(6, 182, 162, 0.25)",
          backgroundColor: (ctx) =>
            makeVerticalGradient(
              ctx.chart.ctx,
              ctx.chart.chartArea,
              pal.dark ? "rgba(0, 229, 190, 0.42)" : "rgba(6, 182, 162, 0.34)",
              pal.dark ? "rgba(31, 94, 140, 0.12)" : "rgba(31, 94, 140, 0.08)"
            ),
        });
      }

      const scales = {
        x: {
          grid: { display: false },
          ticks: { color: pal.muted, maxRotation: 0, autoSkipPadding: 14, font: { size: 11 } },
          border: { color: pal.grid },
        },
        y: {
          beginAtZero: true,
          position: "left",
          grid: { color: pal.grid },
          ticks: {
            color: pal.muted,
            font: { size: 11 },
            callback: (v) =>
              state.evolucaoMode === "coletas" ? v : Number(v).toLocaleString("pt-BR") + " kg",
          },
          border: { display: false },
        },
      };

      if (state.evolucaoMode === "ambos") {
        scales.y1 = {
          beginAtZero: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { color: pal.cyan, precision: 0, font: { size: 11 } },
          border: { display: false },
        };
      }

      state.charts.evolucao = new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          animation: { duration: 650, easing: "easeOutQuart" },
          plugins: {
            qualyNeonGlow: { enabled: true, blur: pal.glowBlur },
            legend: {
              labels: {
                color: pal.text,
                usePointStyle: true,
                pointStyle: "circle",
                padding: 14,
                font: { size: 12, weight: "600" },
              },
            },
            tooltip: {
              ...baseTooltip(pal),
              callbacks: {
                label: (item) => {
                  if (item.dataset.label.includes("kg")) {
                    return " " + item.dataset.label + ": " + fmtKg(item.parsed.y);
                  }
                  return " " + item.dataset.label + ": " + item.parsed.y;
                },
              },
            },
          },
          scales,
        },
      });
    }

    function renderStatus(data, pal) {
      const canvas = document.getElementById("chart-status");
      if (!canvas) return;
      const st = data.por_status || { labels: [], valores: [] };
      const total = st.valores.reduce((a, b) => a + b, 0);
      const concluidas = st.valores[0] || 0;
      const taxa = total > 0 ? Math.round((concluidas / total) * 100) : 0;

      const hudVal = document.getElementById("donut-hud-val");
      const hudLbl = document.getElementById("donut-hud-lbl");
      if (hudVal) hudVal.textContent = total > 0 ? taxa + "%" : "—";
      if (hudLbl) hudLbl.textContent = total > 0 ? "Concluídas" : "Sem dados";

      const bgColors = pal.dark
        ? [
            "rgba(78, 255, 117, 0.78)",
            "rgba(0, 229, 190, 0.72)",
            "rgba(56, 189, 248, 0.68)",
            "rgba(148, 163, 184, 0.45)",
          ]
        : [
            "rgba(47, 168, 54, 0.84)",
            "rgba(6, 182, 162, 0.78)",
            "rgba(31, 94, 140, 0.76)",
            "rgba(107, 114, 128, 0.55)",
          ];
      const borderColors = [pal.neonGreen, pal.cyan, pal.steel, pal.slate];

      state.charts.status = new Chart(canvas, {
        type: "doughnut",
        data: {
          labels: st.labels,
          datasets: [
            {
              data: total > 0 ? st.valores : [1],
              backgroundColor:
                total > 0
                  ? bgColors
                  : [pal.dark ? "rgba(57, 211, 83, 0.14)" : "rgba(47, 168, 54, 0.12)"],
              borderColor: total > 0 ? borderColors : [pal.grid],
              borderWidth: total > 0 ? 2 : 1,
              hoverOffset: total > 0 ? 10 : 0,
              _glowColor: pal.dark ? "rgba(57, 211, 83, 0.45)" : "rgba(47, 168, 54, 0.25)",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "68%",
          animation: { duration: 700 },
          plugins: {
            qualyNeonGlow: { enabled: total > 0, blur: pal.glowBlur },
            legend: {
              position: "bottom",
              labels: {
                color: pal.text,
                usePointStyle: true,
                pointStyle: "circle",
                padding: 12,
                font: { size: 11.5, weight: "600" },
              },
            },
            tooltip: {
              ...baseTooltip(pal),
              enabled: total > 0,
              callbacks: {
                label: (item) => {
                  const pct = total ? ((item.parsed / total) * 100).toFixed(1) : "0.0";
                  return ` ${item.label}: ${item.parsed} (${pct}%)`;
                },
              },
            },
          },
        },
      });
    }

    function renderBairros(data, pal) {
      const canvas = document.getElementById("chart-bairros");
      if (!canvas) return;
      const items = data.por_bairro || [];
      const labels = items.length ? items.map((b) => b.bairro) : ["Sem registros"];
      const vals = items.length
        ? items.map((b) => (state.bairroMode === "kg" ? b.kg_total : b.total_coletas))
        : [0];

      state.charts.bairros = new Chart(canvas, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: state.bairroMode === "kg" ? "Volume por Bairro (kg)" : "Coletas por Bairro",
              data: vals,
              borderRadius: 10,
              maxBarThickness: 24,
              borderWidth: 1.5,
              borderColor: pal.neonGreen,
              _glowColor: pal.dark ? "rgba(78, 255, 117, 0.42)" : "rgba(47, 168, 54, 0.24)",
              backgroundColor: (ctx) =>
                makeHorizontalGradient(
                  ctx.chart.ctx,
                  ctx.chart.chartArea,
                  pal.dark ? "rgba(16, 185, 129, 0.24)" : "rgba(31, 94, 140, 0.22)",
                  pal.dark ? "rgba(78, 255, 117, 0.76)" : "rgba(47, 168, 54, 0.78)"
                ),
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 600 },
          plugins: {
            qualyNeonGlow: { enabled: items.length > 0, blur: pal.glowBlur - 2 },
            legend: { display: false },
            tooltip: {
              ...baseTooltip(pal),
              callbacks: {
                label: (item) =>
                  state.bairroMode === "kg"
                    ? " " + fmtKg(item.parsed.x)
                    : " " + item.parsed.x + " coletas",
              },
            },
          },
          scales: {
            x: {
              beginAtZero: true,
              grid: { color: pal.grid },
              ticks: {
                color: pal.muted,
                font: { size: 11 },
                callback: (v) =>
                  state.bairroMode === "kg" ? Number(v).toLocaleString("pt-BR") + " kg" : v,
              },
              border: { display: false },
            },
            y: {
              grid: { display: false },
              ticks: { color: pal.text, font: { size: 11.5, weight: "600" } },
              border: { color: pal.grid },
            },
          },
        },
      });
    }

    function renderFrota(data, pal) {
      const canvas = document.getElementById("chart-frota");
      if (!canvas) return;
      const veics = data.por_veiculo || [];
      const labels = veics.length
        ? veics.map((v) => `${v.placa} (${v.tipo_label || v.tipo})`)
        : ["Sem veículos"];
      const vals = veics.length
        ? veics.map((v) => (state.frotaMode === "kg" ? v.kg_total : v.total_coletas))
        : [0];

      state.charts.frota = new Chart(canvas, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: state.frotaMode === "kg" ? "Carga Transportada (kg)" : "Coletas Realizadas",
              data: vals,
              borderRadius: 12,
              maxBarThickness: 44,
              borderWidth: 1.6,
              borderColor: pal.emerald,
              _glowColor: pal.dark ? "rgba(0, 229, 190, 0.45)" : "rgba(16, 185, 129, 0.25)",
              backgroundColor: (ctx) =>
                makeVerticalGradient(
                  ctx.chart.ctx,
                  ctx.chart.chartArea,
                  pal.dark ? "rgba(0, 229, 190, 0.72)" : "rgba(16, 185, 129, 0.76)",
                  pal.dark ? "rgba(57, 211, 83, 0.14)" : "rgba(47, 168, 54, 0.14)"
                ),
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 600 },
          plugins: {
            qualyNeonGlow: { enabled: true, blur: pal.glowBlur - 2 },
            legend: { display: false },
            tooltip: {
              ...baseTooltip(pal),
              callbacks: {
                label: (item) =>
                  state.frotaMode === "kg"
                    ? " " + fmtKg(item.parsed.y)
                    : " " + item.parsed.y + " coletas",
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: pal.text, font: { size: 11, weight: "600" } },
              border: { color: pal.grid },
            },
            y: {
              beginAtZero: true,
              grid: { color: pal.grid },
              ticks: {
                color: pal.muted,
                font: { size: 11 },
                precision: state.frotaMode === "coletas" ? 0 : undefined,
                callback: (v) =>
                  state.frotaMode === "kg" ? Number(v).toLocaleString("pt-BR") + " kg" : v,
              },
              border: { display: false },
            },
          },
        },
      });
    }

    function renderAll() {
      destroyAll();
      const data = activeData();
      const pal = themePalette();
      renderEvolucao(data, pal);
      renderStatus(data, pal);
      renderBairros(data, pal);
      renderFrota(data, pal);

      const simBadge = document.getElementById("qualy-sim-badge");
      if (simBadge) {
        simBadge.classList.toggle("d-none", !state.useSim);
      }
      const simBtn = document.getElementById("btn-toggle-sim");
      if (simBtn) {
        simBtn.textContent = state.useSim
          ? "Voltar aos dados reais"
          : "Visualizar prévia simulada";
      }
    }

    // Bind segmented buttons
    document.querySelectorAll("[data-chart-switch]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-chart-switch");
        const mode = btn.getAttribute("data-mode");
        const group = btn.closest(".qualy-seg-group");
        if (group) {
          group.querySelectorAll(".qualy-seg-btn").forEach((b) => b.classList.remove("active"));
        }
        btn.classList.add("active");
        if (target === "evolucao") state.evolucaoMode = mode;
        if (target === "bairros") state.bairroMode = mode;
        if (target === "frota") state.frotaMode = mode;
        renderAll();
      });
    });

    const simBtn = document.getElementById("btn-toggle-sim");
    if (simBtn) {
      simBtn.addEventListener("click", () => {
        state.useSim = !state.useSim;
        renderAll();
      });
    }

    window.addEventListener("qualy:themechange", renderAll);
    renderAll();
  };

  // =========================================================================
  // Mini-gráfico Translúcido no Painel Inicial (/)
  // =========================================================================
  window.initHomeMiniChart = function (series7d) {
    let chartInst = null;

    function draw() {
      const canvas = document.getElementById("chart-home-7d");
      if (!canvas) return;
      if (chartInst) chartInst.destroy();

      const pal = themePalette();
      const ev = series7d.evolucao_diaria || [];
      const labels = ev.map((d) => d.label);
      const vals = ev.map((d) => d.kg_transportados);
      const colVals = ev.map((d) => d.total_coletas);

      chartInst = new Chart(canvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Kg reciclados",
              data: vals,
              tension: 0.42,
              fill: true,
              borderWidth: 2.4,
              borderColor: pal.neonGreen,
              _glowColor: pal.dark ? "rgba(78, 255, 117, 0.55)" : "rgba(47, 168, 54, 0.35)",
              pointRadius: 3.5,
              pointHoverRadius: 6,
              pointBackgroundColor: pal.neonGreen,
              backgroundColor: (ctx) =>
                makeVerticalGradient(
                  ctx.chart.ctx,
                  ctx.chart.chartArea,
                  pal.dark ? "rgba(57, 211, 83, 0.42)" : "rgba(47, 168, 54, 0.28)",
                  "rgba(16, 185, 129, 0.01)"
                ),
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            qualyNeonGlow: { enabled: true, blur: pal.glowBlur },
            legend: { display: false },
            tooltip: {
              ...baseTooltip(pal),
              callbacks: {
                label: (item) =>
                  ` ${fmtKg(item.parsed.y)} (${colVals[item.dataIndex] || 0} coletas)`,
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: pal.muted, font: { size: 10.5 } },
              border: { display: false },
            },
            y: {
              beginAtZero: true,
              grid: { color: pal.grid },
              ticks: {
                color: pal.muted,
                font: { size: 10.5 },
                maxTicksLimit: 4,
              },
              border: { display: false },
            },
          },
        },
      });
    }

    window.addEventListener("qualy:themechange", draw);
    draw();
  };
})();
