# Setup Debezium Connector
Write-Host "Configuring Debezium connector..." -ForegroundColor Cyan
$response = curl -X POST http://localhost:8084/connectors -H "Content-Type: application/json" -d "@debezium/connector-config.json"
Write-Host $response
Write-Host "`nVerifying connector..." -ForegroundColor Cyan
curl http://localhost:8084/connectors
Write-Host "`nConnector status:" -ForegroundColor Cyan
curl http://localhost:8084/connectors/postgres-connector/status




