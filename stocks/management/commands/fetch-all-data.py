from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Runs Command analyze_stocks, update_historical_data, kelly_exp, and calculate_scores sequentially'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting the sequence...'))

        # Run Command 1
        self.stdout.write('Executing: Command analyze_stocks')
        call_command('analyze_stocks') 

        # Run Command 2
        self.stdout.write('Executing: Command update_historical_data')
        call_command('update_historical_data')

        # Run Command 2-2
        self.stdout.write('Executing: Command compound_profit_price')
        call_command('compound_profit_price')

        # Run Command 2-3
        self.stdout.write('Executing: Command kelly_exp')
        call_command('kelly_exp')

        # Run Command 3
        self.stdout.write('Executing: Command calculate_scores')
        call_command('calculate_scores')

        self.stdout.write(self.style.SUCCESS('All commands finished successfully!'))