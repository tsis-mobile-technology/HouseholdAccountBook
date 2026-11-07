# SSL 인증서 배치 안내

이 디렉터리에 보유 중인 SSL 인증서와 개인키를 아래 파일명 중 하나로 넣어두시면 `run_unix.sh` 실행 시 자동으로 HTTPS 모드로 시작됩니다.

### 지원 파일명:
- **인증서 파일 (Cert / Fullchain)**:
  - `cert.pem`
  - `fullchain.pem`
  - `certificate.crt`
  - `server.crt`
- **개인키 파일 (Private Key)**:
  - `key.pem`
  - `privkey.pem`
  - `private.key`
  - `server.key`

*참고: 다른 경로의 인증서를 사용하고 싶으시다면 프로젝트 루트에 `.env` 파일을 생성하고 `SSL_CERTFILE` 및 `SSL_KEYFILE`에 경로를 지정하시면 됩니다.*
