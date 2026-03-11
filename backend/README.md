## Deployment

Sample config.toml

```toml
[authentication]
access_token_expire_minutes = 15
algorithm = "EdDSA"
D3HUB_PKPATH = "~/.ssh/d3annotation" # although this can also be set as an env variable
```

### Private key for JSON Web Tokens

The [config](src/ahbackend/config/__init__.py) searches for a private key in the location defined by `D3HUB_PKPATH`. You have to set this variable either in config.toml as above or as an environment variable in your system.
