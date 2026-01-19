
            Vector3 heroScale = transform.localScale;
            if (heroScale != _storedScale)
            {
                ClientSend.PlayerScale(heroScale);
                _storedScale = heroScale;
                Vector3 heroScale = transform.localScale;
                if (heroScale != _storedScale)
                {
                    ClientSend.PlayerScale(heroScale);
                    _storedScale = heroScale;
                }   
            }
        }