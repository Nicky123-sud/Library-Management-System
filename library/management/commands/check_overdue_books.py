from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from twilio.rest import Client
from django.conf import settings
from datetime import timedelta
from library.models import Reservation, Loan, Fine # Ensure this is the correct model
import logging
from datetime import datetime
from library.utils import calculate_fine

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for overdue books and notify users via email and SMS'

    def handle(self, *args, **kwargs):
        # Initialize Twilio client
        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Get the current date
        now = timezone.now().date()
        self.stdout.write("Starting overdue book check...")

        # Reservations due in 2 days
        reminder_period = timedelta(days=2)
        upcoming_due_date = now + reminder_period
        # Query for reservations due within 2 days and status = 'borrowed'
        upcoming_reservations = Reservation.objects.filter(
            return_date__lte=upcoming_due_date,
            return_date__gte=now,
            status='borrowed'
        )

        # Send reminder notifications for books due soon
        if upcoming_reservations.exists():
            for reservation in upcoming_reservations:
                user = reservation.user
                book_title = reservation.book.title
                due_date = reservation.return_date.strftime("%Y-%m-%d")

                # Send email reminder
                try:
                    send_mail(
                        'Book Due Soon: Reminder',
                        f'Hello {user.username},\n\nYour book "{book_title}" is due for return on {due_date}. Please return it on time.\n\nThank you!',
                        '<EMAIL>',  # Replace with sender's email
                        [user.email],
                        fail_silently=False,
                    )
                    logger.info(f"Email reminder sent to {user.email} for '{book_title}' due on {due_date}.")
                except Exception as e:
                    logger.error(f"Error sending email to {user.email} for '{book_title}': {e}")

                # Send SMS reminder
                if user.profile.phone_number:
                    try:
                        twilio_client.messages.create(
                            body=f'Hello {user.username}, your book "{book_title}" is due for return on {due_date}. Please return it to avoid penalties.',
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=user.profile.phone_number
                        )
                        logger.info(f"SMS reminder sent to {user.profile.phone_number} for '{book_title}' due on {due_date}.")
                    except Exception as e:
                        logger.error(f"Error sending SMS to {user.profile.phone_number} for '{book_title}': {e}")

                # Log to console for testing purposes
                self.stdout.write(self.style.SUCCESS(
                    f'Reminder sent (email and SMS) for "{book_title}" reserved by {user.username}, due on {due_date}.'
                ))
        else:
            self.stdout.write(self.style.SUCCESS("No books due soon."))

        # Query for overdue reservations
        overdue_reservations = Reservation.objects.filter(
            return_date__lt=now,
            status='borrowed'  # Adjust if there's a different field or value indicating overdue
        )

        # Send overdue notifications
        if overdue_reservations.exists():
            for reservation in overdue_reservations:
                user = reservation.user
                book_title = reservation.book.title
                overdue_date = reservation.return_date.strftime("%Y-%m-%d")

                # Send overdue email
                try:
                    send_mail(
                        'Overdue Book Notice',
                        f'Hello {user.username},\n\nYour book "{book_title}" was due on {overdue_date} and is now overdue. Please return it as soon as possible to avoid penalties.\n\nThank you!',
                        '<EMAIL>',  # Replace with sender's email
                        [user.email],
                        fail_silently=False,
                    )
                    logger.info(f"Overdue email sent to {user.email} for '{book_title}' overdue since {overdue_date}.")
                except Exception as e:
                    logger.error(f"Error sending overdue email to {user.email} for '{book_title}': {e}")

                # Send overdue SMS notifications
                if user.profile.phone_number:
                    try:
                        twilio_client.messages.create(
                            body=f'Hello {user.username}, your book "{book_title}" was due on {overdue_date}. Please return it to avoid penalties.',
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=user.profile.phone_number
                        )
                        logger.info(f"Overdue SMS sent to {user.profile.phone_number} for '{book_title}' overdue since {overdue_date}.")
                    except Exception as e:
                        logger.error(f"Error sending overdue SMS to {user.profile.phone_number} for '{book_title}': {e}")

                # Log to console
                self.stdout.write(self.style.WARNING(
                    f'Overdue notice sent (email and SMS) for "{book_title}" reserved by {user.username}, overdue since {overdue_date}.'
                ))
        else:
            self.stdout.write(self.style.SUCCESS("No overdue books found."))

        self.stdout.write("Overdue book check complete.")

        #Overdue loans
    class Command(BaseCommand):
        help = 'Check for overdue books and create fines if necessary'

        def handle(self, *args, **kwargs):
            overdue_loans = Loan.objects.filter(due_date__lt=date.today(), returned=False)

            for loan in overdue_loans:
                fine_amount = calculate_fine(loan.due_date)

                # Create or update the fine
                Fine.objects.update_or_create(
                    user=loan.user,
                    loan=loan,
                    defaults={
                        'amount': fine_amount,
                        'due_date': loan.due_date,
                        'is_paid': False,
                    }
                )
                print(f"Fine of ${fine_amount} created for {loan.user.username} on Loan ID {loan.id}")

            self.stdout.write(self.style.SUCCESS('Overdue books and fines processed.'))