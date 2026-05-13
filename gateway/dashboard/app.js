const $ = (id) => document.getElementById(id);
let cluster = null;

const notes = {
  raft: `<p><b>Raft</b> sends requests to a strong leader. The leader appends the command to its log, sends <code>AppendEntries</code> to followers, waits for majority ACK, commits the entry, then tells followers the updated commit index.</p>`,
  paxos: `<p><b>Paxos</b> uses proposal numbers and a quorum of acceptors. A proposer sends <code>Prepare</code>, receives <code>Promise</code>, sends <code>Accept</code>, then learners learn the chosen value after majority acceptance.</p>`,
  zab: `<p><b>Zab</b> is ZooKeeper Atomic Broadcast. A primary is selected through recovery, followers synchronize with the primary history, then client requests are broadcast as <code>PROPOSE → ACK → COMMIT</code> with ordered zxids.</p>`
};

async function api(path, method = 'GET', body = null) {
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : null
  });
  return await res.json();
}

function roleFor(node, algorithm) {
  if (!node.alive) return 'failed';
  if (algorithm === 'raft') return node.raft.role;
  if (algorithm === 'zab') return node.zab.role;
  if (node.paxos.learned.length) return 'learner';
  if (node.paxos.accepted_value) return 'acceptor';
  return 'ready';
}

function logFor(node, algorithm) {
  if (algorithm === 'raft') return node.raft.log.map(e => `#${e.index}:${e.value}${e.committed ? ' ✓' : ''}`);
  if (algorithm === 'zab') return node.zab.log.map(e => `${e.zxid}:${e.value}${e.committed ? ' ✓' : ''}`);
  return node.paxos.learned.map(e => `${e.proposal_number}:${e.value}`);
}

function renderNodes() {
  const alg = $('algorithm').value;
  const root = $('nodes');
  root.innerHTML = '';
  if (!cluster) return;
  for (const [id, node] of Object.entries(cluster.nodes)) {
    if (node.error) {
      root.innerHTML += `<div class="node failed"><h3>${id}<span class="tag">down</span></h3><p>${node.error}</p></div>`;
      continue;
    }
    const role = roleFor(node, alg);
    const classes = ['node', role === 'leader' ? 'leader' : '', role === 'primary' ? 'primary' : '', !node.alive ? 'failed' : ''].join(' ');
    const log = logFor(node, alg).map(x => `<span>${x}</span>`).join('') || '<em>No log entries</em>';
    const meta = alg === 'raft'
      ? `term=${node.raft.term}, commitIndex=${node.raft.commit_index}`
      : alg === 'zab'
      ? `epoch=${node.zab.epoch}, deliveredZxid=${node.zab.delivered_zxid}`
      : `promised=${node.paxos.promised_number}, accepted=${node.paxos.accepted_number}`;
    root.innerHTML += `
      <div class="${classes}">
        <h3>${id}<span class="tag">${role}</span></h3>
        <div>${node.alive ? 'Alive' : 'Failed'}</div>
        <div class="kv">${meta}</div>
        <div class="kv"><b>State machine:</b><br>${JSON.stringify(node.kv)}</div>
        <div class="log"><b>Log:</b><br>${log}</div>
      </div>`;
  }
}

function renderTrace() {
  const root = $('trace');
  root.innerHTML = '';
  if (!cluster) return;
  const alg = $('algorithm').value;
  const trace = cluster.trace.filter(e => e.algorithm === alg || e.algorithm === 'admin').slice(-120).reverse();
  if (!trace.length) {
    root.innerHTML = '<p>No protocol events yet.</p>';
    return;
  }
  trace.forEach((e, i) => {
    root.innerHTML += `<div class="event ${e.kind}"><b>${e.node}</b> · ${e.kind}<br>${e.message}<small>${new Date(e.time * 1000).toLocaleTimeString()} · ${e.algorithm}</small></div>`;
  });
}

async function refresh() {
  cluster = await api('/api/status');
  $('algorithmNotes').innerHTML = notes[$('algorithm').value];
  renderNodes();
  renderTrace();
}

async function sendRequest() {
  const alg = $('algorithm').value;
  const value = $('requestValue').value;
  const result = await api(`/api/${alg}/request`, 'POST', { value });
  $('lastResult').textContent = JSON.stringify(result.result || result, null, 2);
  await refresh();
}

$('sendBtn').onclick = sendRequest;
$('resetBtn').onclick = async () => { $('lastResult').textContent = JSON.stringify(await api('/api/reset', 'POST'), null, 2); await refresh(); };
$('refreshBtn').onclick = refresh;
$('raftElectBtn').onclick = async () => { $('lastResult').textContent = JSON.stringify(await api('/api/raft/elect', 'POST'), null, 2); await refresh(); };
$('zabRecoverBtn').onclick = async () => { $('lastResult').textContent = JSON.stringify(await api('/api/zab/recover', 'POST'), null, 2); await refresh(); };
$('failBtn').onclick = async () => { const n = $('nodeSelector').value; $('lastResult').textContent = JSON.stringify(await api(`/api/nodes/${n}/fail`, 'POST'), null, 2); await refresh(); };
$('recoverBtn').onclick = async () => { const n = $('nodeSelector').value; $('lastResult').textContent = JSON.stringify(await api(`/api/nodes/${n}/recover`, 'POST'), null, 2); await refresh(); };
$('algorithm').onchange = () => { $('algorithmNotes').innerHTML = notes[$('algorithm').value]; renderNodes(); renderTrace(); };

refresh();
setInterval(refresh, 3500);
