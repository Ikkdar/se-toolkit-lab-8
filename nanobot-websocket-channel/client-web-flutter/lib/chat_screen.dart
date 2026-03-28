import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'llm_service.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final Map<String, dynamic>? structured;

  ChatMessage({required this.text, required this.isUser, this.structured})
      : timestamp = DateTime.now();

  factory ChatMessage.fromBotResponse(String content) {
    final parsed = _tryParseStructured(content);
    if (parsed != null) {
      final displayText = parsed['content'] as String? ?? content;
      return ChatMessage(text: displayText, isUser: false, structured: parsed);
    }
    return ChatMessage(text: content, isUser: false);
  }

  static Map<String, dynamic>? _tryParseStructured(String content) {
    try {
      final json = jsonDecode(content) as Map<String, dynamic>;
      final type = json['type'] as String?;
      if (type == 'choice' || type == 'confirm' || type == 'composite') {
        return json;
      }
    } catch (_) {}
    return null;
  }
}

class ChatScreen extends StatefulWidget {
  final String accessKey;
  final VoidCallback? onDisconnect;

  const ChatScreen({super.key, required this.accessKey, this.onDisconnect});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  late final LlmService _llm = LlmService();
  StreamSubscription<String>? _sub;
  bool _isLoading = false;
  Timer? _responseTimeout;

  static const _timeoutDuration = Duration(seconds: 90);

  @override
  void initState() {
    super.initState();
    _llm.connect(accessKey: widget.accessKey);
    _sub = _llm.responses.listen(
      (content) {
        _responseTimeout?.cancel();
        setState(() {
          _messages.add(ChatMessage.fromBotResponse(content));
          _isLoading = false;
        });
        _scrollToBottom();
      },
      onError: (_) => _handleDisconnect(),
      onDone: () => _handleDisconnect(),
    );
    _addBotMessage(
      'Connected to Nanobot!\n\n'
      'Start by asking:\n'
      '• What can you do in this system?\n'
      '• What tools do you have right now?\n'
      '• Ask one question about the LMS or the system state.\n\n'
      'I am more than a chat UI only when the agent has tools, skills, and memory. '
      'Try discovering those capabilities from the conversation itself.',
    );
  }

  void _handleDisconnect() {
    _responseTimeout?.cancel();
    if (!mounted) return;
    setState(() => _isLoading = false);
    _addBotMessage('Connection lost. Please refresh the page to reconnect.');
  }

  void _startResponseTimeout() {
    _responseTimeout?.cancel();
    _responseTimeout = Timer(_timeoutDuration, () {
      if (!mounted) return;
      setState(() => _isLoading = false);
      _addBotMessage(
        'The assistant is taking too long to respond. '
        'Try again or refresh the page.',
      );
    });
  }

  void _addBotMessage(String text) {
    setState(() {
      _messages.add(ChatMessage(text: text, isUser: false));
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _isLoading) return;

    _controller.clear();
    setState(() {
      _messages.add(ChatMessage(text: trimmed, isUser: true));
      _isLoading = true;
    });
    _scrollToBottom();

    _llm.send(trimmed);
    _startResponseTimeout();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Nanobot'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
        actions: [
          if (widget.onDisconnect != null)
            IconButton(
              icon: const Icon(Icons.logout),
              tooltip: 'Disconnect',
              onPressed: widget.onDisconnect,
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length + (_isLoading ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length) {
                  return _buildLoadingBubble();
                }
                return _buildMessageBubble(_messages[index]);
              },
            ),
          ),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    final isUser = message.isUser;
    if (!isUser && message.structured != null) {
      return _buildStructuredMessage(message.structured!);
    }
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isUser
              ? Theme.of(context).colorScheme.primary
              : Colors.grey[200],
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
        ),
        child: SelectableText(
          message.text,
          style: TextStyle(
            color: isUser ? Colors.white : Colors.black87,
            fontSize: 15,
          ),
        ),
      ),
    );
  }

  Widget _buildStructuredMessage(Map<String, dynamic> data) {
    final type = data['type'] as String;
    switch (type) {
      case 'choice':
        return _buildChoiceMessage(data);
      case 'confirm':
        return _buildConfirmMessage(data);
      case 'composite':
        return _buildCompositeMessage(data);
      default:
        return _buildBotBubble(data['content'] as String? ?? '');
    }
  }

  Widget _buildChoiceMessage(Map<String, dynamic> data) {
    final content = data['content'] as String? ?? '';
    final options = (data['options'] as List<dynamic>?) ?? [];
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.grey[200],
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(16),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (content.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: SelectableText(
                  content,
                  style: const TextStyle(color: Colors.black87, fontSize: 15),
                ),
              ),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: options.map<Widget>((opt) {
                final label = opt['label'] as String? ?? '';
                final value = opt['value'] as String? ?? label;
                return ActionChip(
                  label: Text(label),
                  onPressed: _isLoading ? null : () => _sendMessage(value),
                  backgroundColor: Colors.white,
                  side: BorderSide(
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  labelStyle: TextStyle(
                    color: Theme.of(context).colorScheme.primary,
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfirmMessage(Map<String, dynamic> data) {
    final content = data['content'] as String? ?? '';
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.grey[200],
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(16),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (content.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: SelectableText(
                  content,
                  style: const TextStyle(color: Colors.black87, fontSize: 15),
                ),
              ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ActionChip(
                  label: const Text('Yes'),
                  onPressed: _isLoading ? null : () => _sendMessage('yes'),
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  side: BorderSide.none,
                  labelStyle: const TextStyle(color: Colors.white),
                ),
                const SizedBox(width: 8),
                ActionChip(
                  label: const Text('No'),
                  onPressed: _isLoading ? null : () => _sendMessage('no'),
                  backgroundColor: Colors.white,
                  side: BorderSide(color: Colors.grey[400]!),
                  labelStyle: const TextStyle(color: Colors.black87),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompositeMessage(Map<String, dynamic> data) {
    final parts = (data['parts'] as List<dynamic>?) ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: parts.map<Widget>((part) {
        final partMap = part as Map<String, dynamic>;
        final type = partMap['type'] as String?;
        if (type == 'choice') return _buildChoiceMessage(partMap);
        if (type == 'confirm') return _buildConfirmMessage(partMap);
        return _buildBotBubble(partMap['content'] as String? ?? '');
      }).toList(),
    );
  }

  Widget _buildBotBubble(String text) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.grey[200],
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(16),
          ),
        ),
        child: SelectableText(
          text,
          style: const TextStyle(color: Colors.black87, fontSize: 15),
        ),
      ),
    );
  }

  Widget _buildLoadingBubble() {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.grey[200],
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(16),
          ),
        ),
        child: const SizedBox(
          width: 48,
          height: 24,
          child: Center(
            child: SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey[300]!)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: 'Ask Nanobot about the system...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(24)),
                ),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
              onSubmitted: _sendMessage,
              enabled: !_isLoading,
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed:
                _isLoading ? null : () => _sendMessage(_controller.text),
            icon: const Icon(Icons.send),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _responseTimeout?.cancel();
    _sub?.cancel();
    _controller.dispose();
    _scrollController.dispose();
    _llm.dispose();
    super.dispose();
  }
}
