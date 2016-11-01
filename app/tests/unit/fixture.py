from app.card_router import ActionCode

card_info = [{
    'id': 1,
    'payment_token': '1111111111111111111112',
    'card_token': '111111111111112',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.ADD,
    'date': 1475920002
}, {
    'id': 2,
    'payment_token': '1111111111111111111113',
    'card_token': '111111111111113',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.ADD,
    'date': 1475920002
}, {
    'id': 1,
    'payment_token': '1111111111111111111112',
    'card_token': '111111111111112',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.DELETE,
    'date': 1476714525

}
]

card_info_reduce = [{
    'id': 1,
    'payment_token': '1111111111111111111112',
    'card_token': '111111111111112',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.ADD,
    'date': 1475920002
}, {
    'id': 2,
    'payment_token': '1111111111111111111113',
    'card_token': '111111111111113',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.ADD,
    'date': 1475920002
}, {
    'id': 3,
    'payment_token': '1111111111111111111114',
    'card_token': '111111111111114',
    'partner_slug': 'test_slug',
    'action_code': ActionCode.DELETE,
    'date': 1476714525

}
]

real_list = [{"id": 1, "card_token": "1111111111111111111111", "payment_token": "1111111111111111111111", "date": 1477389675, "partner_slug": "visa"}, {"id": 2, "card_token": "2222222222222222222222222", "payment_token": "222222222222222222", "date": 1476807590, "partner_slug": "visa"}]
