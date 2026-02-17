#!/usr/bin/env python
"""
Setup script for Banking Customer Support Database
Run this once to initialize the database
"""

import sys
from database import init_db, seed_test_data


def main():
    print("=" * 60)
    print("Banking Customer Support AI - Database Setup")
    print("=" * 60)

    try:
        # Initialize database
        print("\n1. Creating database tables...")
        engine, SessionLocal = init_db()
        print("   ✓ Tables created successfully")

        # Optional: seed test data
        print("\n2. Would you like to add sample test data? (y/n)")
        response = input("   > ").strip().lower()

        if response == "y":
            seed_test_data()
            print("   ✓ Sample data added")
        else:
            print("   • Skipping sample data")

        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nDatabase location: ./banking_support.db")
        print("\nTo use the database in your code:")
        print("  from db.database import get_session, SupportTicket")
        print("  from db.db_utils import TicketManager, LogManager")
        print("\nExample:")
        print("  ticket_id = TicketManager.create_ticket(...)")
        print("  LogManager.log_interaction(...)")
        print("\n")

    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
