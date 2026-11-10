# Changelog

## Version 0.2.0

The first fully working version of the package.

### Added

- Connection to the real Vodacom Tanzania M-Pesa service, in both testing (sandbox) and live mode
- Asking a customer to pay, which they confirm with their M-Pesa PIN on their phone
- Sending money to a customer
- Sending money to another business
- Checking the status of a transaction
- Reversing (refunding) a payment
- Automatic handling of M-Pesa sign-in, so you don't have to manage it yourself
- Checks on phone numbers, amounts and references before anything is sent
- Clear, readable messages for every M-Pesa error
- Setup from a simple settings file
- Support for payment results that M-Pesa sends back to your website later
- A ready-made Django add-on that saves payments and shows them in the admin panel
- A command-line tool for quick checks
- Examples for Flask, FastAPI and plain Python
- A full set of automated tests
- A quick start guide and a testing guide

### Changed

- Setup now needs your full M-Pesa account details, not just the API key
- The package now needs Python 3.10 or newer

### Fixed

- The package can now be installed and used without errors
- Django is no longer required unless you use the Django add-on

## Version 0.1.0

- First release
