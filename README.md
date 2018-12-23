# Exim module for Webmin

This is a [Webmin](http://www.webmin.com) module for administering the Exim MTA (mail server).

## Main features:
* View log files
  - main
  - reject
  - panic
* View message queue and manage messages in the queue
  - Display headers
  - Display body
  - Give up message
  - Thaw message
  - Send message
  - Remove message
  - Add a recipient
  - Edit sender
  - Mark all as sent
* View Exim statistics
  - Summary
  - Deliveries by transport
  - Messages received
  - Deliveries
  - Time spent on queue: all messages
  - Time spent on queue: messages with at least one remote delivery
  - Relayed messages
  - Top 10 sending host by message count
  - Top 10 sending host by volume
  - Top 10 local senders by message count
  - Top 10 local senders by volume
  - Top 10 hosts destination by message count
  - Top 10 hosts destination by volume
  - Top 10 local destinations by message count
  - Top 10 local destinations by volume
  - List of errors

## Change log

Major changes for each version are documented in the [CHANGELOG](CHANGELOG).

## License

This module is published under the [GNU GENERAL PUBLIC LICENSE](LICENSE).

Please also consider the included [NOTICE](NOTICE) regarding Exim.

## Acknowledgements

This module was mostly developed by Alexandre Mathieu <mtlx@free.fr>, published on http://mtlx.free.fr/webmin/exim/.

Versions 0.2.7 and later were adapted by TweakM.

## Languages

Currently this module supports these languages:
* English
* French
