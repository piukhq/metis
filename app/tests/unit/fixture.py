from app.card_router import ActionCode

card_info = [{
    'id': 1,
    'payment_token': '1111111111111111111112',
    'card_token': '111111111111112',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.ADD
}, {
    'id': 2,
    'payment_token': '1111111111111111111113',
    'card_token': '111111111111113',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.ADD
}, {
    'id': 1,
    'payment_token': '1111111111111111111112',
    'card_token': '111111111111112',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.DELETE
}
]
