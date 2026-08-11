from app.agents.order_agent import process_message

def run_test(test_num, name, text, phone):
    print(f"\n--- Test {test_num}: {name} ---")
    print(f"User ({phone}): '{text}'")
    res = process_message(text, phone)
    print(f"Intent: {res['intent']}")
    print(f"Extracted: {res['extracted']}")
    print(f"AI Reply: {res['response']}")

# Test 1: Complete Order (Valid Distributor, triggers Credit Hold)
run_test(1, "Complete Order", "100ml coconut oil ke 30 carton credit pe bhej do", "919876543210")

# Test 2: Incomplete Order (Missing Quantity)
run_test(2, "Incomplete Order", "Coconut oil chahiye", "919876543210")

# Test 3: Inquiry (Reads from Catalog Service)
run_test(3, "Inquiry", "100ml coconut oil ka rate kya hai?", "919876543210")

# Test 4: Unknown Distributor (Rule 1 Enforcement)
run_test(4, "Unknown Distributor", "100ml coconut oil ke 10 carton bhej do", "999999999999")