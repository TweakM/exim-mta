#!/usr/bin/perl

require 5;

use strict;  # Be strict !
use integer; # Be fast !
use vars qw(%config %text $exim);

# Helpers sub
sub display_error_page
{
    header($text{error}, '', undef, 1, 1);
    print '<hr/>', "\n";
    print '<p>', text(@_), '</p>', "\n";
    print '<br/>', "\n";
    print '<hr/>', "\n";
    footer('/', $text{index_return});
}

sub parse_CGI
  {
    my $cgi = shift;
    my $length = shift;
    my $valid_chars = shift;
    my @in = @_;

    my $valid_cgi = substr $cgi, 0, $length;
    eval "\$valid_cgi =~ tr/$valid_chars//c";
    if (@in) {
      return (grep /^$valid_cgi$/, @in)?$valid_cgi:undef
    }
    return $valid_cgi;
  }
1;
