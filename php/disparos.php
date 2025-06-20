<?php
// Ferramenta simples para manipular a tabela de disparos via CLI
// Usa variaveis de ambiente para se conectar ao PostgreSQL

$host = getenv('PG_HOST') ?: 'localhost';
$port = getenv('PG_PORT') ?: '5432';
$db   = getenv('PG_DB')   ?: 'ced';
$user = getenv('PG_USER') ?: 'ced';
$pass = getenv('PG_PASS') ?: 'ced';

$dsn = "pgsql:host=$host;port=$port;dbname=$db";
$options = [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION];
$pdo = new PDO($dsn, $user, $pass, $options);

$acao = $argv[1] ?? '';
if ($acao === 'create') {
    $lista    = isset($argv[2]) ? (int)$argv[2] : 0;
    $mensagem = isset($argv[3]) ? (int)$argv[3] : 0;
    $agendado = $argv[4] ?? null;
    if (!$lista || !$mensagem) {
        fwrite(STDERR, "Uso: php disparos.php create <lista_id> <mensagem_id> [agendado_para]\n");
        exit(1);
    }
    $stmt = $pdo->prepare('INSERT INTO disparos (lista_id, mensagem_id, agendado_para) VALUES (:lista, :msg, :ag) RETURNING id');
    $stmt->execute([':lista' => $lista, ':msg' => $mensagem, ':ag' => $agendado]);
    $id = $stmt->fetchColumn();
    echo "Disparo criado com ID {$id}\n";
} elseif ($acao === 'list') {
    foreach ($pdo->query('SELECT id, lista_id, mensagem_id, agendado_para, status, criado_em FROM disparos ORDER BY id') as $row) {
        echo json_encode($row, JSON_UNESCAPED_UNICODE) . PHP_EOL;
    }
} else {
    echo "Uso:\n";
    echo "  php disparos.php create <lista_id> <mensagem_id> [agendado_para]\n";
    echo "  php disparos.php list\n";
}
?>

